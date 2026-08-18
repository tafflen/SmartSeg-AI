from __future__ import annotations

import asyncio
import os
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from models import Resident, SyncQueue, Transaction, User, WasteEvent, get_db
from services.reward_engine import calculate_reward
from services.sms import send_sms_async
from schemas import WasteEventCreate, WasteEventResponse
from security import require_roles

router = APIRouter(prefix="/waste", tags=["waste"])


class LiveFeed:
    def __init__(self) -> None: self.connections: set[WebSocket] = set()
    async def connect(self, socket: WebSocket) -> None: await socket.accept(); self.connections.add(socket)
    def disconnect(self, socket: WebSocket) -> None: self.connections.discard(socket)
    async def publish(self, payload: dict) -> None:
        for socket in list(self.connections):
            try: await socket.send_json(payload)
            except Exception: self.disconnect(socket)


live_feed = LiveFeed()


@router.post("/event", response_model=WasteEventResponse)
async def create_event(payload: WasteEventCreate, db: Session = Depends(get_db)):
    user = None
# async def create_event(payload: WasteEventCreate, db: Session = Depends(get_db),
#                        user: User = Depends(require_roles("resident", "rwa", "gcc", "admin"))):
    # if user.role == "resident" and user.resident_id != payload.resident_id:
    if user and user.role == "resident" and user.resident_id != payload.resident_id:
        raise HTTPException(403, "Residents may only submit their own events")
    if not db.get(Resident, payload.resident_id):
        raise HTTPException(404, "Resident not found")
    existing = db.query(WasteEvent).filter_by(client_event_uuid=payload.client_event_uuid).first()
    if existing:  # Durable idempotency: retrying the same AI-engine UUID returns the prior event.
        await live_feed.publish(WasteEventResponse.model_validate(existing).model_dump(mode="json"))
        return existing
    # One SQLite commit records classification, queue state, wallet credit, and ledger entry.
    points = 0 if payload.resident_id == 0 else calculate_reward(payload.category, payload.weight_grams, payload.confidence_score)
    event = WasteEvent(**payload.model_dump(exclude={"timestamp", "reward_points"}), reward_points=points,
                       timestamp=payload.timestamp or datetime.now(timezone.utc).isoformat())
    db.add(event); db.flush(); db.add(SyncQueue(waste_event_id=event.id))
    resident = db.get(Resident, payload.resident_id)
    before_balance = resident.wallet_balance
    if points:
        resident.wallet_balance += points
        db.add(Transaction(resident_id=resident.id, type="earn", points=points, note=f"Waste: {payload.category}"))
    db.commit(); db.refresh(event)
    if payload.resident_id == 0:
        send_sms_async(os.getenv("ADMIN_PHONE"), "SmartSeg: An unregistered card used the station.")
    elif points and int(before_balance) // 100 < int(resident.wallet_balance) // 100:
        send_sms_async(resident.phone, f"SmartSeg: You earned {points} pts! Total: {resident.wallet_balance:.0f} pts.")
    await live_feed.publish(WasteEventResponse.model_validate(event).model_dump(mode="json"))
    return event


@router.get("/live", response_model=list[WasteEventResponse])
def live(limit: int = Query(20, ge=1, le=100), db: Session = Depends(get_db),
         user: User = Depends(require_roles("resident", "rwa", "gcc", "admin"))):
    query = db.query(WasteEvent).order_by(WasteEvent.id.desc())
    if user.role == "resident": query = query.filter_by(resident_id=user.resident_id)
    return query.limit(limit).all()


async def websocket_live_feed(websocket: WebSocket):
    # Production should authenticate this socket (JWT header/query) and rate-limit connections.
    await live_feed.connect(websocket)
    try:
        while True: await websocket.receive_text()  # keeps connection alive; events are server-pushed.
    except WebSocketDisconnect:
        live_feed.disconnect(websocket)
