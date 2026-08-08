"""PN532 serial-bridge NFC reader with backend-first, local-first identity resolution.

The PN532 bridge firmware should print one line per tap: ``UID:04A1B2C3``.
This port is independent of the Arduino conveyor port.
"""
from __future__ import annotations

import json
import logging
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import config
import db

LOGGER = logging.getLogger(__name__)


class NFCReader:
    def __init__(self, mock_mode: bool = config.MOCK_MODE) -> None:
        self.mock_mode = mock_mode
        self.serial: Any | None = None
        self._mock_index = 0

    def open(self) -> None:
        if self.mock_mode:
            return
        import serial
        self.serial = serial.Serial(config.NFC_SERIAL_PORT, config.NFC_SERIAL_BAUD_RATE, timeout=0.2)
        LOGGER.info("Opened PN532 NFC serial reader on %s", config.NFC_SERIAL_PORT)

    def close(self) -> None:
        if self.serial:
            self.serial.close(); self.serial = None

    def read_uid(self, timeout_seconds: float) -> str | None:
        if self.mock_mode:
            # A seeded real UID keeps the entire demo functional without hardware.
            uid = db.DEMO_RESIDENTS[self._mock_index % len(db.DEMO_RESIDENTS)][1]
            self._mock_index += 1
            return uid
        if not self.serial:
            self.open()
        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            line = self.serial.readline().decode("ascii", errors="ignore").strip().upper()
            if line.startswith("UID:") and len(line) > 4:
                return line[4:].replace(" ", "")
        return None

    def resolve_uid(self, uid: str) -> dict[str, Any]:
        """Prefer the backend; a backend outage falls back to the shared local SQLite DB."""
        try:
            request = Request(f"{config.BACKEND_URL}/nfc/scan", data=json.dumps({"nfc_uid": uid}).encode(),
                              headers={"Content-Type": "application/json", "Authorization": f"Bearer {config.NFC_API_TOKEN}"}, method="POST")
            with urlopen(request, timeout=config.NFC_BACKEND_TIMEOUT_SECONDS) as response:
                payload = json.loads(response.read().decode())
            if payload.get("status") == "UNREGISTERED_CARD":
                return {"id": 0, "name": "Guest", "nfc_uid": uid, "phone": None, "unregistered": True}
            # The shared SQLite profile provides phone/wallet details omitted from scan response.
            local = db.get_resident_by_nfc(uid)
            return local or {"id": payload["resident_id"], "name": payload["name"], "nfc_uid": uid, "phone": None, "unregistered": False}
        except (HTTPError, URLError, TimeoutError, OSError, ValueError) as error:
            # Offline-first contract: a local lookup must never block physical segregation.
            LOGGER.warning("Backend NFC resolution unavailable (%s); using local SQLite", error)
            local = db.get_resident_by_nfc(uid)
            if local:
                return {**local, "unregistered": False}
            return {"id": 0, "name": "Guest", "nfc_uid": uid, "phone": None, "unregistered": True}

    def scan_and_resolve(self, attempts: int = 3) -> dict[str, Any] | None:
        for attempt in range(1, attempts + 1):
            LOGGER.info("Please tap your NFC card (%s/%s)", attempt, attempts)
            uid = self.read_uid(config.NFC_TAP_TIMEOUT_SECONDS)
            if uid:
                return self.resolve_uid(uid)
        LOGGER.error("No NFC tap after %s attempts; skipping this waste cycle", attempts)
        return None
