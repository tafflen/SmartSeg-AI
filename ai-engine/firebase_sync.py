"""Connectivity-tolerant Firestore mirror worker for locally committed events."""
from __future__ import annotations

import logging
import threading
import time
from datetime import datetime
from typing import Any

import config
import db

LOGGER = logging.getLogger(__name__)


class FirebaseSyncWorker:
    def __init__(self) -> None:
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._client: Any | None = None

    def start(self) -> None:
        if not config.SYNC_ENABLED:
            LOGGER.info("Firebase sync disabled (offline-first default)")
            return
        self._thread = threading.Thread(target=self._run, name="firebase-sync", daemon=True)
        self._thread.start()

    def trigger(self) -> None:
        # The periodic worker owns retries; this lightweight hook keeps the main loop non-blocking.
        if config.SYNC_ENABLED:
            LOGGER.debug("Firebase sync queued")

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=2)

    def _run(self) -> None:
        while not self._stop.wait(config.SYNC_INTERVAL_SECONDS):
            try:
                client = self._get_client()
                for event in db.get_unsynced_events():
                    if not self._ready_for_retry(event):
                        continue
                    try:
                        self._push_event(client, event)
                        db.mark_synced(event["id"])
                    except Exception:
                        db.mark_sync_failure(event["id"])
                        LOGGER.exception("Firestore sync failed for event %s; it remains local", event["id"])
            except Exception:
                # Credential, network, or service failure never interrupts segregation.
                LOGGER.exception("Firebase worker unavailable; will retry later")

    def _get_client(self) -> Any:
        if self._client is None:
            import firebase_admin
            from firebase_admin import credentials, firestore
            if not config.FIREBASE_CREDENTIALS_PATH:
                raise RuntimeError("SMARTSEG_FIREBASE_CREDENTIALS is not configured")
            if not firebase_admin._apps:
                firebase_admin.initialize_app(credentials.Certificate(config.FIREBASE_CREDENTIALS_PATH))
            self._client = firestore.client()
        return self._client

    @staticmethod
    def _ready_for_retry(event: dict[str, Any]) -> bool:
        if not event["last_attempt"]:
            return True
        delay = min(2 ** int(event["retry_count"]), config.SYNC_MAX_BACKOFF_SECONDS)
        return (time.time() - datetime.fromisoformat(event["last_attempt"]).timestamp()) >= delay

    @staticmethod
    def _push_event(client: Any, event: dict[str, Any]) -> None:
        client.collection("residents").document(str(event["resident_id"])).set({
            "name": event["resident_name"], "nfc_uid": event["nfc_uid"], "phone": event["phone"],
            "wallet_balance": event["wallet_balance"],
        }, merge=True)
        client.collection("waste_events").document(str(event["id"])).set({
            key: event[key] for key in ("resident_id", "category", "confidence_score", "weight_grams", "reward_points", "timestamp")
        })
