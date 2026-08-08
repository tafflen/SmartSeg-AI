from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from models import Resident, User, get_db
from schemas import NFCRegisterRequest, NFCScanRequest, NFCScanResponse
from security import require_roles

router = APIRouter(prefix="/nfc", tags=["nfc"])
last_seen_uid: str | None = None


@router.post("/scan", response_model=NFCScanResponse)
def scan(payload: NFCScanRequest, db: Session = Depends(get_db), user: User = Depends(require_roles("resident", "rwa", "gcc", "admin"))):
    # ai-engine/nfc_reader.py resolves scanned UIDs through this endpoint first.
    global last_seen_uid
    last_seen_uid = payload.nfc_uid
    resident = db.query(Resident).filter_by(nfc_uid=payload.nfc_uid).first()
    if not resident:
        return NFCScanResponse(resident_id=0, name="Guest", status="UNREGISTERED_CARD")
    return NFCScanResponse(resident_id=resident.id, name=resident.name, status="REGISTERED")


@router.get("/last-seen")
def get_last_seen(user: User = Depends(require_roles("admin"))):
    return {"nfc_uid": last_seen_uid}


@router.post("/register", response_model=NFCScanResponse)
def register_card(payload: NFCRegisterRequest, db: Session = Depends(get_db), user: User = Depends(require_roles("admin"))):
    resident = db.get(Resident, payload.resident_id)
    if not resident:
        raise HTTPException(404, "Resident not found")
    existing = db.query(Resident).filter(Resident.nfc_uid == payload.nfc_uid, Resident.id != resident.id).first()
    if existing:
        raise HTTPException(409, "NFC card already belongs to another resident")
    resident.nfc_uid = payload.nfc_uid
    db.commit()
    return NFCScanResponse(resident_id=resident.id, name=resident.name, status="REGISTERED")
