"""SmartSeg FastAPI application. Run from backend/: uvicorn main:app --reload"""
from __future__ import annotations

import logging
import sqlite3
import time
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from models import DATABASE_PATH
from routes import admin_routes, auth_routes, gcc_routes, nfc_routes, resident_routes, rwa_routes, waste_routes

LOGGER = logging.getLogger("smartseg.backend")
PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = PROJECT_ROOT / "database" / "schema.sql"

app = FastAPI(title="SmartSeg API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)


@app.middleware("http")
async def request_logging(request: Request, call_next):
    started = time.perf_counter()
    response = await call_next(request)
    LOGGER.info("%s %s -> %s in %.1fms", request.method, request.url.path, response.status_code,
                (time.perf_counter() - started) * 1000)
    # Production hardening: add a reverse-proxy or middleware rate limiter per client/IP.
    return response


def ensure_database() -> None:
    """Create a new DB from schema and migrate the two v2 API columns on existing demos."""
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DATABASE_PATH)
    try:
        # On a Prompt-1 database the new index references a column that does not
        # exist yet; apply the additive migration below, then rerun the schema.
        try:
            connection.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
        except sqlite3.OperationalError as error:
            if "no such column" not in str(error):
                raise
        for table, column, statement in (
            ("users", "resident_id", "ALTER TABLE users ADD COLUMN resident_id INTEGER"),
            ("waste_events", "client_event_uuid", "ALTER TABLE waste_events ADD COLUMN client_event_uuid TEXT"),
        ):
            columns = {row[1] for row in connection.execute(f"PRAGMA table_info({table})")}
            if column not in columns:
                connection.execute(statement)
        connection.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_users_resident_id ON users(resident_id)")
        connection.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_waste_events_client_event_uuid_unique ON waste_events(client_event_uuid)")
        connection.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
        # ID 0 is the durable guest identity for unregistered cards; it earns no rewards.
        connection.execute("INSERT OR IGNORE INTO residents(id, name, nfc_uid, phone) VALUES (0, 'Guest', 'UNREGISTERED', NULL)")
        connection.commit()
    finally:
        connection.close()


@app.on_event("startup")
def startup() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    ensure_database()
    LOGGER.info("SmartSeg SQLite database ready at %s", DATABASE_PATH)


@app.get("/health", tags=["system"])
def health():
    return {"status": "ok", "database": str(DATABASE_PATH)}


app.include_router(auth_routes.router)
app.include_router(resident_routes.router)
app.include_router(rwa_routes.router)
app.include_router(gcc_routes.router)
app.include_router(nfc_routes.router)
app.include_router(waste_routes.router)
app.include_router(admin_routes.router)
app.add_api_websocket_route("/ws/live-feed", waste_routes.websocket_live_feed)
