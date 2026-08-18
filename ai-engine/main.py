"""SmartSeg trigger-driven AI engine entry point."""

#uvicorn main:app --reload
from __future__ import annotations

import json
import logging
import random
import time
from typing import Any

import config
import db
from camera import Camera
from backend_bridge import BackendBridge
from detector import WasteDetector
from firebase_sync import FirebaseSyncWorker
from nfc_reader import NFCReader
from serial_comm import SerialCommunicator, SerialEvent
from sms_notifier import build_provider, send_async

LOGGER = logging.getLogger("smartseg")


def get_current_resident(nfc_reader: NFCReader) -> dict[str, Any] | None:
    """Read a physical tap with bounded retries; never hold a conveyor cycle forever."""
    return nfc_reader.scan_and_resolve(attempts=3)


def sensor_context(serial: SerialCommunicator, ir_event: SerialEvent) -> dict[str, str]:
    context = {"proximity": "UNKNOWN", "rain": "DRY"}
    # Backward-compatible support for requested IR_TRIGGERED:PROX=...,RAIN=... firmware.
    if ir_event.argument:
        for pair in ir_event.argument.split(","):
            if "=" in pair:
                key, value = pair.split("=", 1)
                context[{"PROX": "proximity", "RAIN": "rain"}.get(key, key.lower())] = value
    # Consume currently queued v1 context events without blocking the classification path.
    for name, key in (("PROXIMITY", "proximity"), ("RAINDROP", "rain")):
        event = serial.wait_for_event(name, timeout=0.01)
        if event and event.argument:
            context[key] = event.argument
    return context


# def fuse_sensor_context(result: dict[str, Any], context: dict[str, str]) -> dict[str, Any]:
def fuse_sensor_context(
    result: dict[str, Any],
    context: dict[str, str],
) -> dict[str, Any]:

    try:
        rain_value = int(float(context["rain"]))
    except (ValueError, TypeError):
        rain_value = 900

    # Rain sensor: higher value = drier, lower value = wetter.
    wet = rain_value < 600

    if wet and result["confidence_score"] < config.BORDERLINE_CONFIDENCE:
        return {
            **result,
            "category": "ORGANIC",
            "sensor_override": "wet_sensor",
        }

    return {
        **result,
        "sensor_override": None,
    }
    # Wetness does not overwrite a strong model result. It only resolves uncertainty safely.
    # wet = context["rain"].upper() in {"WET", "HIGH", "1", "TRUE"}
    rain_value = float(context["rain"]) if context["rain"].replace(".", "", 1).isdigit() else 900
    wet = rain_value < 600
    if wet and result["confidence_score"] < config.BORDERLINE_CONFIDENCE:
        result = {**result, "category": "ORGANIC", "sensor_override": "wet_borderline"}
    else:
        result = {**result, "sensor_override": None}
    return result


def reward_for(weight_grams: int, category: str, confidence_score: float) -> int:
    """Offline mirror of backend.services.reward_engine.calculate_reward."""
    factors = {"PLASTIC": 1.5, "METAL": 2.0, "ORGANIC": 1.0, "OTHER": 0.5}
    points = (weight_grams // 10) * factors[category]
    return int(points * (0.5 if confidence_score < 0.6 else 1.0))


def persist_completed_event(resident: dict[str, Any], category: str, confidence: float, weight_grams: int,
                            sensor_context: dict[str, str], sync_worker: FirebaseSyncWorker, bridge: BackendBridge, sms_provider: Any) -> None:
    reward_points = reward_for(weight_grams, category, confidence)
    event_id, before, after, client_event_uuid = db.insert_waste_event(resident["id"], category, confidence, weight_grams, reward_points)
    sync_worker.trigger(); bridge.notify()
    if resident.get("unregistered"):
        send_async(sms_provider, config.ADMIN_PHONE, f"SmartSeg: Unregistered card {resident['nfc_uid']} used the station.")
    elif int(before) // config.SMS_REWARD_THRESHOLD < int(after) // config.SMS_REWARD_THRESHOLD:
        send_async(sms_provider, resident["phone"], f"SmartSeg: You earned {reward_points} pts! Total: {after:.0f} pts.")
    print(json.dumps({"event_id": event_id, "client_event_uuid": client_event_uuid, "resident_id": resident["id"], "category": category,
                      "confidence_score": confidence, "weight_grams": weight_grams, "reward_points": reward_points,
                      "sensor_context": sensor_context}), flush=True)


# def process_cycle(serial: SerialCommunicator, camera: Camera, detector: WasteDetector,
#                   nfc_reader: Any, sync_worker: FirebaseSyncWorker, bridge: BackendBridge, sms_provider: Any) -> None:
#     resident = get_current_resident(nfc_reader)
#     if not resident:
#         LOGGER.warning("No recognized NFC resident; ignoring IR cycle")
#         return
#     ir_event = serial.wait_for_event("IR_TRIGGERED")
#     assert ir_event is not None
#     context = sensor_context(serial, ir_event)
#     try:
#         result = fuse_sensor_context(detector.classify(camera.capture_frame()), context)
#     except Exception as error:
#         LOGGER.error("Camera/inference unavailable: %s. Set SMARTSEG_SIMULATE_MODE=true to continue without hardware.", error)
#         serial.send_command("CONVEYOR_STOP")
#         return
#     category = result["category"]
#     if not serial.classify_and_wait(category):
#         return
#     weight_grams = random.randint(50, 500)  # TODO: real HX711 load-cell input.
#     persist_completed_event(resident, category, result["confidence_score"], weight_grams, context, sync_worker, bridge, sms_provider)

def process_cycle(
    serial: SerialCommunicator,
    camera: Camera,
    detector: WasteDetector,
    nfc_reader: Any,
    sync_worker: FirebaseSyncWorker,
    bridge: BackendBridge,
    sms_provider: Any,
) -> None:

    # ---------------------------------------------------------
    # STEP 1: Wait for the REAL Arduino IR trigger first.
    # ---------------------------------------------------------
    #
    # The Arduino sends:
    #
    # EVT:<id>:IR_TRIGGERED:PROX=<value>,RAIN=<value>
    #
    # This means the physical IR sensor has detected an object.
    #
    input("\nPress ENTER to trigger waste detection... ")

    ir_event = SerialEvent(
        event_id=int(time.time()),
        name="IR_TRIGGERED",
        argument="PROX=1000,RAIN=900",
    )

    LOGGER.info("Manual ENTER trigger received")

    LOGGER.info(
        "Real Arduino IR trigger received: event=%s argument=%s",
        ir_event.event_id,
        ir_event.argument,
    )


    # ---------------------------------------------------------
    # STEP 2: Read proximity + rain values from Arduino.
    # ---------------------------------------------------------

    context = sensor_context(serial, ir_event)

    LOGGER.info(
        "Sensor context: proximity=%s, rain=%s",
        context["proximity"],
        context["rain"],
    )


    # ---------------------------------------------------------
    # STEP 3: NFC is OPTIONAL during prototype testing.
    # ---------------------------------------------------------
    #
    # IMPORTANT:
    # We do NOT wait for NFC here unless REQUIRE_NFC=true.
    #
    # This allows the real camera + YOLO pipeline to be tested
    # even when the PN532 is not being used.
    #

    resident = None

    if config.REQUIRE_NFC:

        LOGGER.info("NFC is required for this run")

        resident = get_current_resident(nfc_reader)

        if not resident:
            LOGGER.warning(
                "NFC is required but no recognized NFC resident was found. "
                "Skipping this waste cycle."
            )
            return

    else:

        LOGGER.info(
            "NFC is optional for prototype testing; "
            "continuing without resident identification."
        )


    # ---------------------------------------------------------
    # STEP 4: Capture REAL camera frame + REAL YOLO inference.
    # ---------------------------------------------------------

    try:

        LOGGER.info("Capturing real camera frame for YOLO inference...")

        frame = camera.capture_frame()

        LOGGER.info("Running YOLO inference...")

        result = detector.classify(frame)

        result = fuse_sensor_context(
            result,
            context,
        )

        LOGGER.info(
            "YOLO result: category=%s confidence=%.3f sensor_override=%s",
            result["category"],
            result["confidence_score"],
            result.get("sensor_override"),
        )

    except Exception as error:

        LOGGER.error(
            "Camera/YOLO inference unavailable: %s",
            error,
        )

        # No motor is connected in the current prototype.
        # We therefore do not send CONVEYOR_STOP here.

        return


    # ---------------------------------------------------------
    # STEP 5: Send classification back to Arduino.
    # ---------------------------------------------------------
    #
    # Current sensor-only Arduino firmware accepts CLASSIFY
    # but does NOT move a servo or stepper.
    #

    category = result["category"]

    LOGGER.info(
        "Sending classification to Arduino: %s",
        category,
    )

    if not serial.classify_and_wait(category):

        LOGGER.error(
            "Arduino did not acknowledge classification: %s",
            category,
        )

        return


    LOGGER.info(
        "Arduino acknowledged classification: %s",
        category,
    )


    # ---------------------------------------------------------
    # STEP 6: Weight is NOT REAL yet.
    # ---------------------------------------------------------
    #
    # There is currently no HX711/load-cell hardware connected.
    #
    # DO NOT pretend this is a real measurement.
    #
    # Therefore, only use the random weight if we explicitly
    # need the old database/reward demo path.
    #

    if resident is None:

        print(
            json.dumps(
                {
                    "status": "AI_CLASSIFICATION_COMPLETE",
                    "resident_id": None,
                    "category": category,
                    "confidence_score": result["confidence_score"],
                    "weight_grams": None,
                    "reward_points": None,
                    "sensor_context": context,
                    "sensor_override": result.get("sensor_override"),
                }
            ),
            flush=True,
        )

        return


    # ---------------------------------------------------------
    # STEP 7: Resident exists -> existing reward/database flow.
    # ---------------------------------------------------------
    #
    # NOTE:
    # Weight is still simulated because the HX711 is not
    # connected yet.
    #

    weight_grams = random.randint(50, 500)

    LOGGER.warning(
        "Weight is currently SIMULATED because no HX711/load cell "
        "is connected: %s g",
        weight_grams,
    )

    persist_completed_event(
        resident,
        category,
        result["confidence_score"],
        weight_grams,
        context,
        sync_worker,
        bridge,
        sms_provider,
    )


def process_simulated_cycle(nfc_reader: NFCReader, sync_worker: FirebaseSyncWorker, bridge: BackendBridge, sms_provider: Any) -> None:
    """Demo-only path: no camera, Arduino, servo, or NFC hardware is touched."""
    resident = get_current_resident(nfc_reader)
    if not resident: return
    category = random.choice(["PLASTIC", "ORGANIC", "METAL", "OTHER"])
    persist_completed_event(resident, category, round(random.uniform(0.45, 0.98), 2), random.randint(50, 500),
                            {"proximity": "SIMULATED", "rain": random.choice(["DRY", "WET"])}, sync_worker, bridge, sms_provider)


def main() -> None:
    logging.basicConfig(level=logging.DEBUG if config.MOCK_MODE else logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    db.initialize_database(seed_demo_data=config.MOCK_MODE)
    io_mock = config.MOCK_MODE or config.SIMULATE_MODE
    serial = SerialCommunicator(mock_mode=io_mock)
    camera = Camera(mock_mode=io_mock)
    detector = WasteDetector(mock_mode=io_mock)
    nfc_reader = NFCReader(mock_mode=io_mock)
    sync_worker = FirebaseSyncWorker()
    bridge = BackendBridge()
    sms_provider = build_provider()
    if not config.SIMULATE_MODE: serial.start()
    nfc_reader.open()
    sync_worker.start()
    bridge.start()
    try:
        while True:
            if config.SIMULATE_MODE:
                process_simulated_cycle(nfc_reader, sync_worker, bridge, sms_provider)
                time.sleep(config.SIMULATE_INTERVAL_SECONDS)
            else:
                process_cycle(serial, camera, detector, nfc_reader, sync_worker, bridge, sms_provider)
    except KeyboardInterrupt:
        LOGGER.info("SmartSeg engine stopped")
    finally:
        sync_worker.stop()
        bridge.stop()
        camera.close()
        if not config.SIMULATE_MODE: serial.close()
        nfc_reader.close()


if __name__ == "__main__":
    main()
