# Installation guide

## Windows setup (primary path)

1. Install Python 3.11, Node.js 20 LTS, Git, and Arduino IDE 2.x. In PowerShell, confirm `py -3.11 --version`, `node --version`, and `npm --version`.
2. Clone/open the SmartSeg project, then create one shared virtual environment:

   ```powershell
   py -3.11 -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r ai-engine\requirements.txt
   pip install -r backend\requirements.txt
   cd frontend; npm install; cd ..
   ```

3. In Arduino IDE, install/select **Arduino AVR Boards**, select **Arduino Uno**, and upload `arduino-firmware/smartseg_firmware.ino`. `Servo.h` ships with the Arduino core. The Uno firmware does not use a PN532 library because NFC runs on its own serial bridge.
4. For the PN532 bridge, use an ESP32/serial-bridge firmware with a PN532 library such as **Adafruit PN532** or **Elechouse PN532**. Configure PN532 UART/HSU mode and make the bridge print `UID:<HEX>` at 115200 baud. See [NFC setup](nfc_setup.md).
5. In Windows Device Manager, note the Uno and PN532 bridge COM ports. Install the CH340/CP210x driver if the board does not appear. Set `SERIAL_PORT=COM3` and `NFC_SERIAL_PORT=COM4` (substitute your actual ports).
6. Set local environment values. For a first demo, use `SMARTSEG_SIMULATE_MODE=true`, keep Firebase disabled, and retain Mock SMS. For PowerShell:

   ```powershell
   $env:SMARTSEG_SIMULATE_MODE='true'
   $env:JWT_SECRET='replace-this-before-a-demo'
   $env:ADMIN_PHONE='+91xxxxxxxxxx'
   ```

7. Run `start_all.bat`, then open `http://localhost:5173`. Use `http://localhost:8000/docs` to create/test API accounts if needed.

## Firebase (optional)

1. Create a Firebase project and enable **Cloud Firestore** in production or test mode appropriate to your demo.
2. Create a service account in Project settings → Service accounts and download its JSON key. Keep it outside version control.
3. Set `SMARTSEG_SYNC_ENABLED=true` and `FIREBASE_CREDENTIALS_PATH=C:\secure\service-account.json`.
4. Start SmartSeg; unsynced local rows remain safe in SQLite and will retry when credentials/network are available.

## Twilio SMS (optional)

1. Create a Twilio account, obtain a verified sender/phone number, and verify the destination during trial mode.
2. Set `SMARTSEG_SMS_PROVIDER=twilio`, `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, and `TWILIO_FROM_PHONE`.
3. Keep `ADMIN_PHONE` configured for unknown-card alerts. Without these values, SmartSeg uses Mock SMS and logs notifications instead of sending them.

## macOS and Linux differences

- Create/activate the environment with `python3.11 -m venv .venv` and `source .venv/bin/activate`.
- Launch with `bash start_all.sh`.
- Serial device names are usually `/dev/cu.usbmodem*` on macOS and `/dev/ttyACM0` or `/dev/ttyUSB0` on Linux. On Linux, add your user to the `dialout` group if serial permission is denied, then log out/in.
- Arduino board/driver setup and PN532 wiring are otherwise identical.
