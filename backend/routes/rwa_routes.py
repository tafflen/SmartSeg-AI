from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from models import Resident, User, WasteEvent, get_db
from schemas import WasteEventResponse
from security import require_roles

router = APIRouter(prefix="/rwa", tags=["rwa"])


@router.get("/dashboard-summary")
def dashboard_summary(db: Session = Depends(get_db), user: User = Depends(require_roles("rwa"))):
    now = datetime.now(timezone.utc); today = now.date().isoformat(); week = (now - timedelta(days=7)).isoformat()
    totals = dict(db.query(WasteEvent.category, func.count(WasteEvent.id)).group_by(WasteEvent.category).all())
    today_totals = dict(db.query(WasteEvent.category, func.count(WasteEvent.id)).filter(WasteEvent.timestamp >= today).group_by(WasteEvent.category).all())
    week_totals = dict(db.query(WasteEvent.category, func.count(WasteEvent.id)).filter(WasteEvent.timestamp >= week).group_by(WasteEvent.category).all())
    return {"scope": "single_society", "by_category": totals, "today_by_category": today_totals, "week_by_category": week_totals,
            "total_residents": db.query(Resident).count(),
            "active_residents_today": db.query(func.count(func.distinct(WasteEvent.resident_id))).filter(WasteEvent.timestamp >= today).scalar() or 0}


@router.get("/residents")
def residents(offset: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=200),
              db: Session = Depends(get_db), user: User = Depends(require_roles("rwa"))):
    rows = db.query(Resident, func.count(WasteEvent.id), func.coalesce(func.sum(WasteEvent.reward_points), 0)).outerjoin(WasteEvent).group_by(Resident.id).offset(offset).limit(limit).all()
    return [{"id": resident.id, "name": resident.name, "nfc_uid": resident.nfc_uid, "phone": resident.phone,
             "wallet_balance": resident.wallet_balance, "event_count": count, "earned_points": points} for resident, count, points in rows]


@router.get("/waste-events", response_model=list[WasteEventResponse])
def waste_events(category: str | None = None, resident_id: int | None = None, from_timestamp: str | None = None,
                 to_timestamp: str | None = None, offset: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=200),
                 db: Session = Depends(get_db), user: User = Depends(require_roles("rwa"))):
    query = db.query(WasteEvent)
    if category: query = query.filter(WasteEvent.category == category.upper())
    if resident_id: query = query.filter(WasteEvent.resident_id == resident_id)
    if from_timestamp: query = query.filter(WasteEvent.timestamp >= from_timestamp)
    if to_timestamp: query = query.filter(WasteEvent.timestamp <= to_timestamp)
    return query.order_by(WasteEvent.id.desc()).offset(offset).limit(limit).all()
