from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from firebase_sync import sync_once
from models import Resident, SyncQueue, User, get_db
from schemas import ResidentCreate, ResidentResponse, ResidentUpdate, SyncQueueResponse
from security import require_roles

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/residents", response_model=ResidentResponse, status_code=201)
def create_resident(payload: ResidentCreate, db: Session = Depends(get_db), user: User = Depends(require_roles("admin"))):
    resident = Resident(**payload.model_dump()); db.add(resident)
    try: db.commit()
    except IntegrityError: db.rollback(); raise HTTPException(409, "NFC UID already exists")
    db.refresh(resident); return resident


@router.get("/residents", response_model=list[ResidentResponse])
def list_residents(offset: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=500), db: Session = Depends(get_db), user: User = Depends(require_roles("admin"))):
    return db.query(Resident).offset(offset).limit(limit).all()


@router.put("/residents/{resident_id}", response_model=ResidentResponse)
def update_resident(resident_id: int, payload: ResidentUpdate, db: Session = Depends(get_db), user: User = Depends(require_roles("admin"))):
    resident = db.get(Resident, resident_id)
    if not resident: raise HTTPException(404, "Resident not found")
    for key, value in payload.model_dump(exclude_unset=True).items(): setattr(resident, key, value)
    try: db.commit()
    except IntegrityError: db.rollback(); raise HTTPException(409, "NFC UID already exists")
    db.refresh(resident); return resident


@router.delete("/residents/{resident_id}", status_code=204)
def delete_resident(resident_id: int, db: Session = Depends(get_db), user: User = Depends(require_roles("admin"))):
    resident = db.get(Resident, resident_id)
    if not resident: raise HTTPException(404, "Resident not found")
    db.delete(resident)
    try: db.commit()
    except IntegrityError: db.rollback(); raise HTTPException(409, "Resident has waste events and cannot be deleted")
    return Response(status_code=204)


@router.get("/sync-queue", response_model=list[SyncQueueResponse])
def sync_queue(db: Session = Depends(get_db), user: User = Depends(require_roles("admin"))):
    return db.query(SyncQueue).order_by(SyncQueue.id.desc()).all()


@router.post("/sync/firebase")
def trigger_firebase_sync(db: Session = Depends(get_db), user: User = Depends(require_roles("admin"))):
    return sync_once(db)
