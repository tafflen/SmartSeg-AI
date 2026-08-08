"""Reliable local-queue to FastAPI live-feed bridge."""
from __future__ import annotations
import json, logging, threading, time
from datetime import datetime
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
import config, db

LOGGER = logging.getLogger(__name__)

class BackendBridge:
    def __init__(self) -> None: self._stop = threading.Event(); self._thread: threading.Thread | None = None
    def start(self) -> None:
        self._thread = threading.Thread(target=self._run, name="backend-bridge", daemon=True); self._thread.start()
    def stop(self) -> None:
        self._stop.set()
        if self._thread: self._thread.join(timeout=2)
    def notify(self) -> None: pass  # Queue is durable; worker polls quickly after local commits.
    def _run(self) -> None:
        while not self._stop.wait(config.BACKEND_BRIDGE_INTERVAL_SECONDS):
            for event in db.pending_backend_events():
                if not self._ready(event): continue
                payload = {key: event[key] for key in ("client_event_uuid", "resident_id", "category", "confidence_score", "weight_grams", "reward_points", "timestamp")}
                try:
                    request = Request(f"{config.BACKEND_URL}/waste/event", data=json.dumps(payload).encode(), method="POST",
                        headers={"Content-Type":"application/json", "Authorization":f"Bearer {config.BACKEND_API_TOKEN}"})
                    with urlopen(request, timeout=config.BACKEND_TIMEOUT_SECONDS): pass
                    db.mark_backend_event_sent(event["id"])
                except (HTTPError, URLError, TimeoutError, OSError) as error:
                    db.mark_backend_event_failed(event["id"])
                    LOGGER.warning("Backend unavailable; retained event %s for retry: %s", event["id"], error)
    @staticmethod
    def _ready(event: dict) -> bool:
        if not event["last_attempt"]: return True
        delay = min(2 ** int(event["retry_count"]), config.BACKEND_BRIDGE_MAX_BACKOFF_SECONDS)
        return time.time() - datetime.fromisoformat(event["last_attempt"]).timestamp() >= delay
