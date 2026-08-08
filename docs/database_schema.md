# SQLite data model

SQLite is the local-first source of truth. `backend_event_queue` is included because Prompt 7 added it to guarantee dashboard delivery without making a physical cycle depend on backend reachability.

```mermaid
erDiagram
    RESIDENTS ||--o{ WASTE_EVENTS : produces
    RESIDENTS ||--o| USERS : "may have login"
    RESIDENTS ||--o{ TRANSACTIONS : owns
    WASTE_EVENTS ||--|| SYNC_QUEUE : queues_for_firebase
    WASTE_EVENTS ||--|| BACKEND_EVENT_QUEUE : queues_for_live_api

    RESIDENTS {
      INTEGER id PK
      TEXT name
      TEXT nfc_uid UK
      TEXT phone
      REAL wallet_balance
      TEXT created_at
    }
    USERS {
      INTEGER id PK
      TEXT username UK
      TEXT password_hash
      TEXT role
      INTEGER resident_id FK_UK
      TEXT created_at
    }
    WASTE_EVENTS {
      INTEGER id PK
      INTEGER resident_id FK
      TEXT category
      REAL confidence_score
      REAL weight_grams
      INTEGER reward_points
      TEXT client_event_uuid UK
      TEXT timestamp
      BOOLEAN synced_to_firebase
    }
    SYNC_QUEUE {
      INTEGER id PK
      INTEGER waste_event_id FK_UK
      TEXT status
      INTEGER retry_count
      TEXT last_attempt
    }
    TRANSACTIONS {
      INTEGER id PK
      INTEGER resident_id FK
      TEXT type
      INTEGER points
      TEXT timestamp
      TEXT note
    }
    BACKEND_EVENT_QUEUE {
      INTEGER id PK
      INTEGER waste_event_id FK_UK
      TEXT client_event_uuid UK
      TEXT status
      INTEGER retry_count
      TEXT last_attempt
    }
```

`residents.id = 0` is reserved as the Guest identity for an unregistered NFC card. Guest events remain auditable but earn zero points. `sync_queue` and `backend_event_queue` are independent: one tracks cloud mirroring; the other retries FastAPI/WebSocket notification.
