# AI engine

Python 3.11 service for trigger-based webcam capture, YOLOv8n inference, sensor fusion, USB serial orchestration, local event persistence, and optional Firebase/SMS delivery.

Its serial contract is defined in `../docs/serial_protocol.md`. It persists completed waste events locally before attempting any optional cloud activity.

## Run the offline demo

```powershell
pip install -r ai-engine/requirements.txt
python ai-engine/main.py
```

`MOCK_MODE` defaults to `true`, creating seeded residents, simulated PN532 NFC taps, serial IR/servo events, camera frames, weights, and Mock SMS output. No Arduino, webcam, Firebase credentials, or Twilio account is required.

To use hardware, set `SMARTSEG_MOCK_MODE=false`, configure the independent `SMARTSEG_SERIAL_PORT` (Arduino) and `SMARTSEG_NFC_SERIAL_PORT` (PN532 bridge), plus `SMARTSEG_NFC_API_TOKEN` for backend resolution. See `../docs/nfc_setup.md`. Firebase is separately opt-in with `SMARTSEG_SYNC_ENABLED=true` and `SMARTSEG_FIREBASE_CREDENTIALS`.
