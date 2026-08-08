# Waste disposal cycle

```mermaid
sequenceDiagram
    autonumber
    actor Resident
    participant NFC as PN532 NFC reader
    participant AI as AI engine (laptop)
    participant API as FastAPI backend
    participant DB as Local SQLite
    participant Uno as Arduino Uno
    participant CV as Camera + YOLOv8n
    participant UI as React dashboard
    participant SMS as SMS provider

    Resident->>NFC: Tap card
    NFC->>AI: UID:<hex> over dedicated serial port
    AI->>API: POST /nfc/scan
    API->>DB: Resolve resident UID
    API-->>AI: Registered resident or UNREGISTERED_CARD
    Note over AI,DB: If API is offline, AI looks up UID in shared local SQLite.
    Resident->>Uno: Place waste on conveyor
    Uno->>AI: EVT:id:IR_TRIGGERED:PROX=x,RAIN=y
    AI->>Uno: ACK:id
    AI->>CV: Capture one frame and infer
    CV-->>AI: Category + confidence
    AI->>AI: Fuse wetness context; calculate reward
    AI->>Uno: CMD:id:CLASSIFY:CATEGORY
    Uno-->>AI: ACK:id
    Uno->>Uno: Route servo and clear conveyor
    Uno->>AI: EVT:id:SERVO_DONE:CATEGORY
    AI->>Uno: ACK:id
    AI->>DB: Atomic event + reward + transaction + sync queues
    AI->>API: POST /waste/event via durable bridge queue
    API->>UI: WebSocket /ws/live-feed event
    API->>SMS: Milestone / redemption / guest notification
    API->>DB: Firebase sync status when enabled
```
