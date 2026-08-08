# PN532 NFC setup

SmartSeg uses a **PN532 NFC module connected to the laptop through a separate USB serial bridge**. This is intentionally independent from the Arduino Uno conveyor connection: the NFC reader identifies the resident before the waste cycle starts.

## Wiring and serial bridge

Use an ESP32 (or comparable USB-capable bridge) running PN532 firmware in UART mode. The bridge connects to the PN532 and emits a line like `UID:04A1B2C3\n` whenever a card is tapped.

| Connection | Bridge pin | PN532 pin | Notes |
| --- | --- | --- | --- |
| UART TX | configurable TX | RX | Cross TX/RX. |
| UART RX | configurable RX | TX | Cross TX/RX. |
| 3.3 V | 3V3 | VCC | PN532 logic should use 3.3 V. |
| Ground | GND | GND | Required common reference. |
| USB | laptop | bridge USB | Appears as the dedicated `SMARTSEG_NFC_SERIAL_PORT` (default `COM4`). |

Set the PN532 board's interface selectors for UART/HSU mode. The bridge and `ai-engine/nfc_reader.py` use **115200 baud, 8N1** by default. This simple line protocol avoids competing with the Arduino motor/sensor serial connection on `SMARTSEG_SERIAL_PORT`.

## Runtime flow

1. The reader captures a UID and the AI engine sends it to `POST /nfc/scan` with `SMARTSEG_NFC_API_TOKEN`.
2. A registered card resolves to its resident profile. An unknown UID returns `UNREGISTERED_CARD`, is handled as resident ID `0` (Guest), and earns no points.
3. If the backend is unavailable, the engine looks up the UID in shared local SQLite so offline segregation continues.
4. An admin signs into `/admin`, taps a card, polls `GET /nfc/last-seen`, selects a resident, then posts the link through `POST /nfc/register`.

## Security note

An NFC UID alone is **not strong authentication**: many UID types can be cloned. For production, combine NFC with a PIN or use encrypted/authenticated NFC tags.
