import time
import msvcrt
import re

import config
from camera import Camera
from detector import WasteDetector


# ============================================================
# CONFIG
# ============================================================

SERIAL_PORT = "COM6"
SERIAL_BAUD = 115200

# Your sensor calibration
RAIN_VERY_WET = 300
RAIN_WET = 600
RAIN_DRY = 900

# YOLO confidence threshold is handled by detector.py/config.py


# ============================================================
# SERIAL
# ============================================================

import serial

s = serial.Serial(
    SERIAL_PORT,
    SERIAL_BAUD,
    timeout=0.1
)

print("CONNECTED")

time.sleep(2)

s.write(b"HELLO:LAPTOP:1\n")

print("SENT HANDSHAKE")
print("Press ENTER to classify waste.")
print("Press Ctrl+C to quit.\n")


# ============================================================
# AI COMPONENTS
# ============================================================

camera = Camera(
    device_index=0,
    mock_mode=config.MOCK_MODE
)

detector = WasteDetector(
    mock_mode=config.MOCK_MODE
)


# ============================================================
# COMMAND ID
# ============================================================

next_command_id = 1


# ============================================================
# SENSOR PARSER
# ============================================================

def parse_sensor_values(text):
    """
    Parse:

        EVT:12:IR_TRIGGERED:PROX=394,RAIN=452

    Returns:

        proximity = 394
        rain = 452
    """

    match = re.search(
        r"PROX=(-?\d+),RAIN=(-?\d+)",
        text
    )

    if not match:
        return None, None

    proximity = int(match.group(1))
    rain = int(match.group(2))

    return proximity, rain


# ============================================================
# SENSOR INTERPRETATION
# ============================================================

def interpret_rain(rain):
    """
    Based on the calibration you provided:

        900-1023 = dry
        300-600  = wet/damp
        <300     = very wet
    """

    if rain < RAIN_VERY_WET:
        return "VERY_WET"

    if rain < RAIN_WET:
        return "WET"

    if rain >= RAIN_DRY:
        return "DRY"

    return "INTERMEDIATE"


def object_present(proximity):
    """
    Proximity is NOT used to identify material.

    It only tells us that something is near the sensor.

    Because your module's idle value can be either high
    or low depending on the module, we don't make a
    hard material decision from proximity.
    """

    return True


# ============================================================
# FINAL DECISION ENGINE
# ============================================================

def make_final_decision(yolo_result, proximity, rain):
    """
    Combines:

        1. YOLO visual classification
        2. Rain/wetness information
        3. Proximity/object-presence information

    Proximity is deliberately NOT treated as metal detection.
    """

    yolo_category = yolo_result.get(
        "category",
        "OTHER"
    ).upper()

    confidence = float(
        yolo_result.get(
            "confidence_score",
            0.0
        )
    )

    low_confidence = yolo_result.get(
        "low_confidence",
        False
    )

    rain_state = interpret_rain(rain)

    print("\n--- DECISION ENGINE ---")
    print(f"PROXIMITY : {proximity}")
    print(f"RAIN      : {rain}")
    print(f"RAIN STATE: {rain_state}")
    print(f"YOLO      : {yolo_category}")
    print(f"CONFIDENCE: {confidence:.3f}")

    # --------------------------------------------------------
    # Strong wetness evidence
    # --------------------------------------------------------

    if rain_state in ("VERY_WET", "WET"):

        # Wetness strongly supports organic waste.
        #
        # If YOLO confidently identifies plastic/metal,
        # don't blindly override it.
        #
        # But if YOLO is weak/unknown, use the sensor evidence.
        if (
            low_confidence
            or yolo_category == "OTHER"
        ):

            final_category = "ORGANIC"

            reason = (
                "YOLO uncertain/unknown + "
                "real rain sensor indicates wet waste"
            )

        elif yolo_category == "ORGANIC":

            final_category = "ORGANIC"

            reason = (
                "YOLO identifies organic waste + "
                "rain sensor confirms wetness"
            )

        else:

            # YOLO has a meaningful visual classification.
            # Keep it unless it is UNKNOWN.
            final_category = yolo_category

            reason = (
                f"YOLO identified {yolo_category}; "
                f"rain sensor indicates {rain_state}"
            )

    # --------------------------------------------------------
    # Dry waste
    # --------------------------------------------------------

    elif rain_state == "DRY":

        if yolo_category in (
            "PLASTIC",
            "METAL",
            "ORGANIC",
            "OTHER"
        ):

            final_category = yolo_category

            reason = (
                f"Dry sensor context + YOLO identified "
                f"{yolo_category}"
            )

        else:

            final_category = "OTHER"

            reason = "Unknown YOLO category"

    # --------------------------------------------------------
    # Intermediate sensor value
    # --------------------------------------------------------

    else:

        if not low_confidence and yolo_category != "OTHER":

            final_category = yolo_category

            reason = (
                "Intermediate rain reading + "
                "usable YOLO classification"
            )

        else:

            final_category = "OTHER"

            reason = (
                "Intermediate rain reading + "
                "weak/unknown YOLO classification"
            )

    print(f"FINAL     : {final_category}")
    print(f"REASON    : {reason}")

    return final_category


# ============================================================
# SEND COMMAND
# ============================================================

def send_command(command, argument=None):

    global next_command_id

    if argument:
        frame = (
            f"CMD:{next_command_id}:"
            f"{command}:{argument}\n"
        )
    else:
        frame = (
            f"CMD:{next_command_id}:"
            f"{command}\n"
        )

    s.write(frame.encode())

    print(f"-> sent {frame.strip()}")

    next_command_id += 1


# ============================================================
# MAIN LOOP
# ============================================================

try:

    while True:

        # ----------------------------------------------------
        # ENTER KEY
        # ----------------------------------------------------

        if msvcrt.kbhit():

            key = msvcrt.getch()

            if key in (b"\r", b"\n"):

                send_command(
                    "MANUAL_TRIGGER"
                )


        # ----------------------------------------------------
        # ARDUINO RESPONSE
        # ----------------------------------------------------

        line = s.readline()

        if not line:
            continue

        text = line.decode(
            errors="replace"
        ).strip()

        if not text:
            continue

        print(f"<- {text}")


        # ----------------------------------------------------
        # ARDUINO EVENTS
        # ----------------------------------------------------

        if text.startswith("EVT:"):

            parts = text.split(":")

            event_id = parts[1]

            # ACK Arduino event
            ack = f"ACK:{event_id}\n"

            s.write(
                ack.encode()
            )

            print(
                f"-> sent {ack.strip()}"
            )


            # ------------------------------------------------
            # SENSOR TRIGGER
            # ------------------------------------------------

            if (
                len(parts) >= 3
                and parts[2] == "IR_TRIGGERED"
            ):

                proximity, rain = parse_sensor_values(
                    text
                )

                if (
                    proximity is None
                    or rain is None
                ):

                    print(
                        "ERROR: Could not parse "
                        "sensor values."
                    )

                    continue


                print("\n==============================")
                print("      WASTE DETECTION")
                print("==============================")

                print(
                    f"REAL SENSOR DATA -> "
                    f"PROX={proximity}, "
                    f"RAIN={rain}"
                )


                # ------------------------------------------------
                # CAMERA
                # ------------------------------------------------

                print(
                    "\nCapturing camera frame..."
                )

                try:

                    frame = camera.capture_frame()

                except Exception as error:

                    print(
                        f"Camera error: {error}"
                    )

                    final_category = "OTHER"

                    send_command(
                        "CLASSIFY",
                        final_category
                    )

                    continue


                # ------------------------------------------------
                # YOLO
                # ------------------------------------------------

                print(
                    "Running YOLO..."
                )

                try:

                    yolo_result = detector.classify(
                        frame
                    )

                except Exception as error:

                    print(
                        f"YOLO error: {error}"
                    )

                    final_category = "OTHER"

                    send_command(
                        "CLASSIFY",
                        final_category
                    )

                    continue


                # ------------------------------------------------
                # DISPLAY YOLO RESULT
                # ------------------------------------------------

                print("\n--- YOLO RESULT ---")

                print(
                    f"Category   : "
                    f"{yolo_result.get('category')}"
                )

                print(
                    f"Confidence : "
                    f"{yolo_result.get('confidence_score')}"
                )

                print(
                    f"Low conf.  : "
                    f"{yolo_result.get('low_confidence')}"
                )

                print(
                    f"Detections : "
                    f"{yolo_result.get('raw_detections')}"
                )


                # ------------------------------------------------
                # SENSOR + YOLO DECISION
                # ------------------------------------------------

                final_category = make_final_decision(
                    yolo_result,
                    proximity,
                    rain
                )


                # ------------------------------------------------
                # SEND FINAL CATEGORY TO ARDUINO
                # ------------------------------------------------

                print(
                    "\nSending final classification "
                    "to Arduino..."
                )

                send_command(
                    "CLASSIFY",
                    final_category
                )

                print(
                    "==============================\n"
                )


except KeyboardInterrupt:

    print(
        "\nStopping..."
    )


finally:

    camera.close()

    s.close()

    print("DONE")