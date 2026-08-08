# Integration fixes

This changelog records the contract issues found while connecting Prompts 1–6 and the fixes applied.

| Area | Mismatch found | Fix applied |
| --- | --- | --- |
| Serial boot frames | Firmware emitted a `READY` line not defined in the v1 grammar; the AI parser reported it as unknown. | Removed `READY`; firmware now starts with the documented `HELLO:ARDUINO:1` frame only. |
| Serial error codes | Firmware used `UNKNOWN_CMD`, `NOT_READY`, and `LINK`, while the protocol only listed a different subset. | Documented the exact firmware error frames in `serial_protocol.md`. |
| Serial retransmission safety | The AI acknowledged duplicate `EVT` frames but put each copy on its event queue, risking duplicate waste rows/rewards. | Added a 30-second recently-seen event-ID cache. Duplicate events are ACKed again but never enqueued; see `ai-engine/tests/test_serial_comm.py`. |
| Arduino disconnect | Serial read/open/write failures could leave the listener unusable. | The AI logs the failure and reopens the configured port every five seconds. Failed commands cannot crash the main loop. |
| Live-dashboard bridge | AI local SQLite writes never reached `/waste/event`, so WebSocket clients had no instant update. | Added persistent `backend_event_queue` records and `BackendBridge`, which retries with exponential backoff and idempotent UUIDs. Existing-event API replays also publish to WebSocket clients. |
| Backend outage | A failed backend POST could have affected physical flow. | The bridge runs after the SQLite transaction; failed calls remain queued locally and retry later. |
| Simulation | `MOCK_MODE` simulated devices but did not provide a dedicated no-hardware event loop. | Added `SMARTSEG_SIMULATE_MODE=true`, which never opens camera/Arduino I/O and creates realistic category, confidence, weight, NFC, reward, and live-feed events on a timer. |
| Database evolution | The schema gained idempotency, transaction, and live-bridge records after initial local databases existed. | Startup initialization applies the schema and additive migrations; SQLAlchemy includes models for all durable tables. |
| Environment naming | Documentation requested common names while code used several `SMARTSEG_*` aliases. | `SERIAL_PORT`, `NFC_SERIAL_PORT`, `YOLO_MODEL_PATH`, `JWT_SECRET`, `DATABASE_URL`, and `FIREBASE_CREDENTIALS_PATH` are now recognized alongside the project aliases. |
| Dashboard outage state | API failures could leave a dashboard without explaining why. | Axios dispatches backend reachability state and the shared shell displays a clear unavailable banner. |
