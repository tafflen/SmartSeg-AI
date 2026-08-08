"""SmartSeg trigger-driven AI engine entry point."""
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


def fuse_sensor_context(result: dict[str, Any], context: dict[str, str]) -> dict[str, Any]:
    # Wetness does not overwrite a strong model result. It only resolves uncertainty safely.
    wet = context["rain"].upper() in {"WET", "HIGH", "1", "TRUE"}
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


def process_cycle(serial: SerialCommunicator, camera: Camera, detector: WasteDetector,
                  nfc_reader: Any, sync_worker: FirebaseSyncWorker, bridge: BackendBridge, sms_provider: Any) -> None:
    resident = get_current_resident(nfc_reader)
    if not resident:
        LOGGER.warning("No recognized NFC resident; ignoring IR cycle")
        return
    ir_event = serial.wait_for_event("IR_TRIGGERED")
    assert ir_event is not None
    context = sensor_context(serial, ir_event)
    try:
        result = fuse_sensor_context(detector.classify(camera.capture_frame()), context)
    except Exception as error:
        LOGGER.error("Camera/inference unavailable: %s. Set SMARTSEG_SIMULATE_MODE=true to continue without hardware.", error)
        serial.send_command("CONVEYOR_STOP")
        return
    category = result["category"]
    if not serial.classify_and_wait(category):
        return
    weight_grams = random.randint(50, 500)  # TODO: real HX711 load-cell input.
    persist_completed_event(resident, category, result["confidence_score"], weight_grams, context, sync_worker, bridge, sms_provider)


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
