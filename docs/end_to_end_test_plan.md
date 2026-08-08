# End-to-end demo test plan

1. Create the virtual environment and install dependencies using the root README. Upload `arduino-firmware/smartseg_firmware.ino` if using hardware.
2. Start the backend, frontend, and AI engine with `bash start_all.sh` (or `start_all.bat` on Windows). Confirm `/health` reports `ok` and open `http://localhost:5173`.
3. For a no-hardware rehearsal, set `SMARTSEG_SIMULATE_MODE=true` before launching. Confirm `[AI]` emits a JSON event every configured interval and the dashboard live feed updates.
4. For the hardware path, set `MOCK_MODE=false`, configure the Arduino and NFC serial ports, and confirm the Arduino emits `HELLO:ARDUINO:1`; the AI must answer `HELLO:LAPTOP:1`.
5. Tap a registered NFC card. Confirm the AI logs the resident lookup. With the backend intentionally stopped, confirm it logs a local SQLite fallback rather than hanging.
6. Place a test item at the conveyor entry. Confirm the Arduino emits `EVT:<id>:IR_TRIGGERED:PROX=<value>,RAIN=<value>` and the AI sends `ACK:<id>`.
7. Confirm the webcam captures one frame, YOLO selects a category, and the AI sends `CMD:<id>:CLASSIFY:<CATEGORY>`.
8. Confirm Arduino returns `ACK:<id>`, moves the servo, clears the item, and emits `EVT:<id>:SERVO_DONE:<CATEGORY>`. The AI must ACK this event.
9. Confirm the local database now has one `waste_events` row, one reward `transactions` row (registered card only), one `sync_queue` row, and one `backend_event_queue` row.
10. Confirm the browser receives the live event through `/ws/live-feed`; the resident history, wallet, and RWA feed should update after refresh/polling.
11. Use enough simulated or weighted events to cross a 100-point boundary. Confirm an SMS provider log such as `SmartSeg: You earned ...` appears. With Mock SMS this is a console log.
12. Redeem points from the resident API/UI flow and confirm the wallet falls, a `redeem` transaction appears, and the redemption SMS/mock log is emitted.
13. Tap an unknown card. Confirm the event is assigned to Guest (`resident_id=0`), earns zero points, and sends the admin SMS/mock notification.
14. Unplug the Arduino during a cycle. Confirm the AI logs the disconnect, retries the port every five seconds, and remains running. Reconnect it and repeat the handshake.
