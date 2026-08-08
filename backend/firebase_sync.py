"""API-triggerable Firebase mirror job; disabled until credentials are configured."""
from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any
from sqlalchemy.orm import Session

from models import Resident, SyncQueue, WasteEvent


def sync_once(db: Session) -> dict[str, int | str]:
    if os.getenv("SMARTSEG_SYNC_ENABLED", "false").lower() != "true":
        return {"status": "disabled", "synced": 0, "failed": 0}
    try:
        import firebase_admin
        from firebase_admin import credentials, firestore
        credential_path = os.getenv("FIREBASE_CREDENTIALS_PATH", os.getenv("SMARTSEG_FIREBASE_CREDENTIALS", ""))
        if not credential_path: raise RuntimeError("SMARTSEG_FIREBASE_CREDENTIALS is not configured")
        if not firebase_admin._apps: firebase_admin.initialize_app(credentials.Certificate(credential_path))
        client: Any = firestore.client()
    except Exception as exc:
        return {"status": f"unavailable: {exc}", "synced": 0, "failed": 0}

    synced = failed = 0
    for event in db.query(WasteEvent).filter_by(synced_to_firebase=False).all():
        queue = event.sync_queue
        try:
            resident: Resident = event.resident
            client.collection("residents").document(str(resident.id)).set({"name": resident.name, "nfc_uid": resident.nfc_uid,
                "phone": resident.phone, "wallet_balance": resident.wallet_balance}, merge=True)
            client.collection("waste_events").document(str(event.id)).set({"resident_id": event.resident_id, "category": event.category,
                "confidence_score": event.confidence_score, "weight_grams": event.weight_grams, "reward_points": event.reward_points,
                "timestamp": event.timestamp})
            event.synced_to_firebase = True; queue.status = "synced"; queue.last_attempt = datetime.now(timezone.utc).isoformat(); synced += 1
        except Exception:
            queue.status = "failed"; queue.retry_count += 1; queue.last_attempt = datetime.now(timezone.utc).isoformat(); failed += 1
    db.commit()
    return {"status": "completed", "synced": synced, "failed": failed}
