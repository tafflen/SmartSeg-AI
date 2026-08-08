# SmartSeg architecture

## Technology decisions

| Area | Decision |
| --- | --- |
| AI engine | Python 3.11, OpenCV, Ultralytics YOLOv8n, pyserial |
| Backend | FastAPI, SQLAlchemy, SQLite for local storage, Firebase Admin SDK for sync, JWT authentication |
| Frontend | React 18, Vite, TailwindCSS, Recharts |
| Firmware | Arduino C++ on an Arduino Uno. The NFC reader is separately connected to the laptop over USB, not to the Arduino. |
| Device communications | USB Serial at **115200 baud**, 8 data bits, no parity, 1 stop bit (8N1), using the text protocol in `serial_protocol.md` |

## Module boundaries

1. **ai-engine** owns camera inference and the live Arduino connection. It consumes Arduino events and sends only protocol commands defined in `serial_protocol.md`. It receives the resident identity from the laptop-side NFC workflow; the Arduino never decides an identity or category.
2. **arduino-firmware** owns IR, proximity, and raindrop sensor readings plus conveyor/servo execution. It reports events and acknowledgements to the AI engine over USB Serial, and does not contain YOLO, business rules, or database code.
3. **backend** owns the REST and JWT boundary for all dashboard clients. It reads/writes the local SQLite database through SQLAlchemy and runs (or hosts) the Firebase synchronization service. Hardware is not exposed through REST without an explicit later API design.
4. **frontend** provides the resident, RWA, and GCC/admin dashboards. It communicates only with backend REST endpoints over HTTP(S), passing JWTs as required; it has no serial or direct database access.
5. **database** owns the durable local-first schema. Both event recording and sync state are committed locally before an asynchronous cloud push. The source-of-truth schema is `../database/schema.sql`.

## Cycle ownership

```text
NFC reader -> laptop resident lookup -> AI engine begins eligible cycle
Arduino IR event -> AI engine inference/decision -> Arduino class command
Arduino completion event -> local waste_events + sync_queue transaction
Backend REST -> frontend dashboards
Background sync -> Firebase Firestore
```

The exact serial framing, ACK behavior, and recovery rules are normative in `serial_protocol.md`; all AI-engine and firmware implementations must conform to them.
