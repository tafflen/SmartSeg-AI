# Arduino firmware

# SmartSeg Arduino firmware

`smartseg_firmware.ino` targets an Arduino Uno and implements the deterministic sensor/motor side of SmartSeg. It has no AI and no NFC reader: NFC connects separately to the laptop.

For the separate PN532-over-serial NFC reader, wiring, environment variables, offline fallback, and prototype security note, see [NFC setup](../docs/nfc_setup.md).

## Wiring map

| Device | Arduino pin | Notes |
| --- | --- | --- |
| IR obstacle sensor, digital output | D2 | Waste-presence trigger. Firmware defaults to an active-HIGH module; change `IR_ACTIVE_HIGH` for active-LOW modules. |
| Proximity sensor, analog output | A0 | Secondary object-context reading, range 0–1023. |
| Raindrop/moisture sensor, analog output | A1 | Wetness-context reading, range 0–1023. |
| SG90 (or similar) servo signal | D9 | Servo ground must share common ground with the Uno. |
| L298N motor driver IN1 | D5 | Conveyor forward direction. |
| L298N motor driver IN2 | D6 | Held LOW for this forward/stop-only prototype. |
| L298N motor driver ENA | D7 | Conveyor enable. Remove any ENA jumper when driven by this pin. |
| Status LED | D13 | Built-in Uno LED is supported. |

> **Power warning:** Do **not** power the servo or conveyor motor from the Uno USB/5 V pin. Use appropriately rated external 5 V supplies (or the motor driver's suitable supply), and connect their ground to Arduino GND. An inadequate shared supply can reset the Uno or damage hardware.

## Serial behavior

The device uses USB Serial at **115200 baud, 8N1** and follows [the v1 protocol](../docs/serial_protocol.md): it starts with `HELLO:ARDUINO:1`, expects `HELLO:LAPTOP:1`, accepts correlated `CMD:<id>:...` commands, returns `ACK:<id>`, and emits `EVT:<id>:...` events. An IR detection emits the Prompt-2 combined sensor-fusion payload:

```text
EVT:12:IR_TRIGGERED:PROX=512,RAIN=720
```

The firmware accepts bare `CLASSIFY:PLASTIC` commands only for manual bench testing; the laptop must use the correlated protocol form.

## LED states

- Solid: idle/ready.
- Fast blink: waste detected; waiting for laptop classification.
- Three slow blinks: timeout, malformed input, or link error.

## Standalone test

1. Upload `smartseg_firmware.ino` using Arduino IDE with board set to **Arduino Uno**.
2. Open Serial Monitor at **115200 baud** with “Newline” line ending. Observe `HELLO:ARDUINO:1`.
3. For the full protocol test, send `HELLO:LAPTOP:1`, then `CMD:101:CLASSIFY:PLASTIC` after causing an IR trigger. Expect `ACK:101` and a later `EVT:<id>:SERVO_DONE:PLASTIC`.
4. For servo-only bench testing, type `CLASSIFY:PLASTIC`; confirm the servo moves to 0°, returns neutral, and emits `SERVO_DONE` event framing.

Keep the conveyor motor disconnected for the first servo-only test, then verify motor-driver polarity and external power separately.
