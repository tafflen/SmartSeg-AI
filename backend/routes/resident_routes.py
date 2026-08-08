from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from models import Transaction, User, WasteEvent, get_db
from schemas import RedeemRequest, ResidentResponse, TransactionResponse, WasteEventResponse
from services.sms import send_sms_async
from security import get_current_user

router = APIRouter(prefix="/resident", tags=["resident"])


def resident_user(user: User = Depends(get_current_user("resident"))) -> User:
    if not user.resident_id:
        raise HTTPException(403, "Resident account is not linked to a resident profile")
    return user


@router.get("/me", response_model=ResidentResponse)
def me(user: User = Depends(resident_user)):
    return user.resident


@router.get("/history", response_model=list[WasteEventResponse])
def history(offset: int = Query(0, ge=0), limit: int = Query(20, ge=1, le=100),
            db: Session = Depends(get_db), user: User = Depends(resident_user)):
    return db.query(WasteEvent).filter_by(resident_id=user.resident_id).order_by(WasteEvent.id.desc()).offset(offset).limit(limit).all()


@router.get("/wallet")
def wallet(user: User = Depends(resident_user)):
    points = user.resident.wallet_balance
    return {"resident_id": user.resident_id, "points": points, "redeemable_value": round(points * 0.10, 2), "currency": "INR"}


@router.get("/transactions", response_model=list[TransactionResponse])
def transactions(offset: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=100), db: Session = Depends(get_db), user: User = Depends(resident_user)):
    return db.query(Transaction).filter_by(resident_id=user.resident_id).order_by(Transaction.id.desc()).offset(offset).limit(limit).all()


@router.post("/redeem")
def redeem(payload: RedeemRequest, db: Session = Depends(get_db), user: User = Depends(resident_user)):
    resident = user.resident
    if resident.wallet_balance < payload.points:
        raise HTTPException(400, "INSUFFICIENT_BALANCE")
    resident.wallet_balance -= payload.points
    db.add(Transaction(resident_id=resident.id, type="redeem", points=payload.points, note="Demo reward redemption"))
    db.commit(); db.refresh(resident)
    send_sms_async(resident.phone, f"SmartSeg: Redeemed {payload.points} pts. Total: {resident.wallet_balance:.0f} pts.")
    return {"status": "REDEEMED", "redeemed_points": payload.points, "wallet_balance": resident.wallet_balance}
