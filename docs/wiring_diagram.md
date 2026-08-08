# Hardware wiring diagram

SmartSeg has two independent USB serial devices: the Arduino Uno handles conveyor sensors and actuators; a PN532 reader uses a small USB serial bridge for resident identity. Keeping them separate ensures the Uno remains a deterministic executor.

```text
                         LAPTOP / AI ENGINE
                    ┌─────────────────────────┐
                    │ USB COM3      USB COM4  │
                    └─────┬───────────┬───────┘
                          │           │
                    Arduino Uno   PN532 serial bridge
                          │           │
       ┌──────────────────┴─────┐     └── 3.3V / GND / UART TX-RX ── PN532 NFC
       │                        │                                  (resident card)
   D2 ◄─ IR digital sensor       │
   A0 ◄─ Proximity analog sensor │
   A1 ◄─ Raindrop analog sensor  │
   D9 ─► SG90 servo signal ──────┼── external regulated 5V
   D5 ─► L298N IN1               │
   D6 ─► L298N IN2               │
   D7 ─► L298N ENA               │
       │                          └── GND ───────────────┐
  D13 ─► Status LED (built-in)                            │
                                                           │
                         external motor supply ─► L298N ─► conveyor DC motor
                                                           │
                         ALL grounds (Uno, L298N, servo, sensors, bridge) ──┘
```

## Connections

| Component | Uno / bridge connection | Electrical note |
| --- | --- | --- |
| IR obstacle sensor | Digital output → D2; VCC/GND | Firmware defaults to active-HIGH. Set `IR_ACTIVE_HIGH=false` for active-LOW modules. |
| Proximity sensor | Analog output → A0 | 0–1023 context reading. Use a 5V-compatible analog module. |
| Raindrop sensor | Analog output → A1 | 0–1023 wetness reading. Keep the sensor board away from splash paths. |
| SG90 servo | Signal → D9 | Use an external regulated 5V rail; share ground with Uno. |
| L298N | IN1 → D5, IN2 → D6, ENA → D7 | Remove ENA jumper when D7 drives ENA. Prototype uses forward/stop only. |
| Conveyor motor | L298N motor output | Power from a motor-rated external supply, never Uno USB 5V. |
| Status LED | D13 | Uno built-in LED; solid idle, fast blink awaiting classification, three slow blinks error. |
| PN532 | USB serial bridge, not Uno | Bridge sends `UID:<HEX>` at 115200 baud. PN532 uses 3.3V logic/UART; see [NFC setup](nfc_setup.md). |

> **Power safety:** Servo and conveyor motor current must not come from the laptop USB or Uno 5V pin. Use appropriately rated external supplies and a common ground. Test the servo before connecting the conveyor motor.

## Approximate prototype bill of materials

Prices are indicative India retail estimates and exclude laptop, fabrication, bins, and shipping.

| Item | Qty | Approx. cost (INR) |
| --- | ---: | ---: |
| Arduino Uno-compatible board | 1 | ₹650–900 |
| IR + analog proximity + raindrop sensor modules | 1 set | ₹250–450 |
| SG90 servo | 1 | ₹180–300 |
| L298N motor driver | 1 | ₹180–280 |
| Small DC conveyor motor / prototype conveyor | 1 | ₹800–2,500 |
| PN532 NFC module | 1 | ₹450–850 |
| ESP32/USB serial bridge | 1 | ₹350–600 |
| External 5V supplies, wiring, terminals | 1 set | ₹500–1,000 |
| **Electronics subtotal** |  | **₹3,360–6,880** |
