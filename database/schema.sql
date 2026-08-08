-- SmartSeg local-first SQLite schema (v1)
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS residents (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    nfc_uid TEXT NOT NULL UNIQUE,
    phone TEXT,
    wallet_balance REAL NOT NULL DEFAULT 0.0 CHECK (wallet_balance >= 0),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('resident', 'rwa', 'gcc', 'admin')),
    resident_id INTEGER UNIQUE,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    ,FOREIGN KEY (resident_id) REFERENCES residents(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS waste_events (
    id INTEGER PRIMARY KEY,
    resident_id INTEGER NOT NULL,
    category TEXT NOT NULL CHECK (category IN ('PLASTIC', 'ORGANIC', 'METAL', 'OTHER')),
    confidence_score REAL CHECK (confidence_score IS NULL OR (confidence_score >= 0 AND confidence_score <= 1)),
    weight_grams REAL CHECK (weight_grams IS NULL OR weight_grams >= 0),
    reward_points INTEGER NOT NULL DEFAULT 0 CHECK (reward_points >= 0),
    client_event_uuid TEXT UNIQUE,
    timestamp TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    synced_to_firebase BOOLEAN NOT NULL DEFAULT 0 CHECK (synced_to_firebase IN (0, 1)),
    FOREIGN KEY (resident_id) REFERENCES residents(id) ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS sync_queue (
    id INTEGER PRIMARY KEY,
    waste_event_id INTEGER NOT NULL UNIQUE,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'failed', 'synced')),
    retry_count INTEGER NOT NULL DEFAULT 0 CHECK (retry_count >= 0),
    last_attempt TEXT,
    FOREIGN KEY (waste_event_id) REFERENCES waste_events(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY,
    resident_id INTEGER NOT NULL,
    type TEXT NOT NULL CHECK (type IN ('earn', 'redeem')),
    points INTEGER NOT NULL CHECK (points > 0),
    timestamp TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    note TEXT,
    FOREIGN KEY (resident_id) REFERENCES residents(id) ON DELETE RESTRICT
);

-- Delivers locally committed events to the live backend/WebSocket without
-- making physical segregation depend on backend availability.
CREATE TABLE IF NOT EXISTS backend_event_queue (
    id INTEGER PRIMARY KEY,
    waste_event_id INTEGER NOT NULL UNIQUE,
    client_event_uuid TEXT NOT NULL UNIQUE,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'failed', 'sent')),
    retry_count INTEGER NOT NULL DEFAULT 0 CHECK (retry_count >= 0),
    last_attempt TEXT,
    FOREIGN KEY (waste_event_id) REFERENCES waste_events(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_residents_nfc_uid ON residents(nfc_uid);
CREATE INDEX IF NOT EXISTS idx_waste_events_timestamp ON waste_events(timestamp);
CREATE INDEX IF NOT EXISTS idx_waste_events_synced_to_firebase ON waste_events(synced_to_firebase);
CREATE INDEX IF NOT EXISTS idx_waste_events_client_event_uuid ON waste_events(client_event_uuid);
CREATE INDEX IF NOT EXISTS idx_sync_queue_status ON sync_queue(status);
CREATE INDEX IF NOT EXISTS idx_transactions_resident_timestamp ON transactions(resident_id, timestamp);
CREATE INDEX IF NOT EXISTS idx_backend_event_queue_status ON backend_event_queue(status);
