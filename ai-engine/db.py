"""Small sqlite3 data-access layer matching database/schema.sql exactly."""
from __future__ import annotations

import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import config

DEMO_RESIDENTS = [
    ("Asha Mehta", "04A1B2C3", "+919000000001"),
    ("Rahul Nair", "04D4E5F6", "+919000000002"),
    ("Fatima Khan", "04112233", "+919000000003"),
]


def _connection(database_path: Path = config.DATABASE_PATH) -> sqlite3.Connection:
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_database(seed_demo_data: bool = False) -> None:
    config.DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _connection() as connection:
        try:
            connection.executescript(config.SCHEMA_PATH.read_text(encoding="utf-8"))
        except sqlite3.OperationalError as error:
            if "no such column" not in str(error):
                raise
        # Keep existing demo databases compatible with the backend's idempotent
        # event and resident-login additions without requiring a manual migration.
        user_columns = {row[1] for row in connection.execute("PRAGMA table_info(users)")}
        event_columns = {row[1] for row in connection.execute("PRAGMA table_info(waste_events)")}
        if "resident_id" not in user_columns:
            connection.execute("ALTER TABLE users ADD COLUMN resident_id INTEGER")
        if "client_event_uuid" not in event_columns:
            connection.execute("ALTER TABLE waste_events ADD COLUMN client_event_uuid TEXT")
        connection.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_users_resident_id ON users(resident_id)")
        connection.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_waste_events_client_event_uuid_unique ON waste_events(client_event_uuid)")
        connection.executescript(config.SCHEMA_PATH.read_text(encoding="utf-8"))
        connection.execute("INSERT OR IGNORE INTO residents(id, name, nfc_uid, phone) VALUES (0, 'Guest', 'UNREGISTERED', NULL)")
        if seed_demo_data:
            connection.executemany(
                "INSERT OR IGNORE INTO residents(name, nfc_uid, phone) VALUES (?, ?, ?)", DEMO_RESIDENTS,
            )


def get_resident_by_nfc(nfc_uid: str) -> dict[str, Any] | None:
    with _connection() as connection:
        row = connection.execute("SELECT * FROM residents WHERE nfc_uid = ?", (nfc_uid,)).fetchone()
    return dict(row) if row else None


def insert_waste_event(resident_id: int, category: str, confidence_score: float,
                       weight_grams: float, reward_points: int, client_event_uuid: str | None = None) -> tuple[int, float, float, str]:
    """Atomically persist the event, enqueue cloud sync, and credit the local wallet."""
    with _connection() as connection:
        before = connection.execute("SELECT wallet_balance FROM residents WHERE id = ?", (resident_id,)).fetchone()
        if before is None:
            raise ValueError(f"Unknown resident id {resident_id}")
        cursor = connection.execute(
            """INSERT INTO waste_events(resident_id, category, confidence_score, weight_grams, reward_points, client_event_uuid)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (resident_id, category, confidence_score, weight_grams, reward_points, client_event_uuid or str(uuid.uuid4())),
        )
        event_id = int(cursor.lastrowid)
        client_event_uuid = client_event_uuid or connection.execute("SELECT client_event_uuid FROM waste_events WHERE id = ?", (event_id,)).fetchone()[0]
        connection.execute("INSERT INTO sync_queue(waste_event_id) VALUES (?)", (event_id,))
        connection.execute("INSERT INTO backend_event_queue(waste_event_id, client_event_uuid) VALUES (?, ?)", (event_id, client_event_uuid))
        # Guest ID 0 still records waste, but unregistered cards never receive points.
        reward_points = reward_points if resident_id != 0 else 0
        connection.execute("UPDATE waste_events SET reward_points = ? WHERE id = ?", (reward_points, event_id))
        connection.execute("UPDATE residents SET wallet_balance = wallet_balance + ? WHERE id = ?", (reward_points, resident_id))
        if reward_points:
            connection.execute("INSERT INTO transactions(resident_id, type, points, note) VALUES (?, 'earn', ?, ?)",
                               (resident_id, reward_points, f"Waste: {category}"))
        after = float(before["wallet_balance"]) + reward_points
    return event_id, float(before["wallet_balance"]), after, client_event_uuid


def pending_backend_events() -> list[dict[str, Any]]:
    with _connection() as connection:
        rows = connection.execute("""SELECT w.*, q.client_event_uuid, q.retry_count, q.last_attempt
            FROM backend_event_queue q JOIN waste_events w ON w.id = q.waste_event_id
            WHERE q.status != 'sent' ORDER BY q.id""").fetchall()
    return [dict(row) for row in rows]


def mark_backend_event_sent(event_id: int) -> None:
    with _connection() as connection:
        connection.execute("UPDATE backend_event_queue SET status='sent', last_attempt=? WHERE waste_event_id=?", (_utc_now(), event_id))


def mark_backend_event_failed(event_id: int) -> None:
    with _connection() as connection:
        connection.execute("UPDATE backend_event_queue SET status='failed', retry_count=retry_count+1, last_attempt=? WHERE waste_event_id=?", (_utc_now(), event_id))


def mark_synced(waste_event_id: int) -> None:
    with _connection() as connection:
        connection.execute("UPDATE waste_events SET synced_to_firebase = 1 WHERE id = ?", (waste_event_id,))
        connection.execute("UPDATE sync_queue SET status = 'synced', last_attempt = ? WHERE waste_event_id = ?",
                           (_utc_now(), waste_event_id))


def get_unsynced_events() -> list[dict[str, Any]]:
    with _connection() as connection:
        rows = connection.execute(
            """SELECT w.*, r.name AS resident_name, r.nfc_uid, r.phone, r.wallet_balance,
                      q.retry_count, q.last_attempt
               FROM waste_events w JOIN residents r ON r.id = w.resident_id
               JOIN sync_queue q ON q.waste_event_id = w.id
               WHERE w.synced_to_firebase = 0 AND q.status != 'synced' ORDER BY w.id"""
        ).fetchall()
    return [dict(row) for row in rows]


def mark_sync_failure(waste_event_id: int) -> None:
    with _connection() as connection:
        connection.execute("""UPDATE sync_queue SET status = 'failed', retry_count = retry_count + 1,
                           last_attempt = ? WHERE waste_event_id = ?""", (_utc_now(), waste_event_id))


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()
