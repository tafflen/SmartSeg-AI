from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from models import Resident, User, get_db
from schemas import LoginRequest, RegisterRequest, TokenResponse
from security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    if db.query(User).filter_by(username=payload.username).first():
        raise HTTPException(409, "Username already exists")
    if payload.role == "resident":
        if not payload.resident_id or not db.get(Resident, payload.resident_id):
            raise HTTPException(422, "A valid resident_id is required for resident accounts")
        if db.query(User).filter_by(resident_id=payload.resident_id).first():
            raise HTTPException(409, "Resident already has a login")
    elif payload.resident_id is not None:
        raise HTTPException(422, "resident_id is only valid for resident accounts")
    user = User(username=payload.username, password_hash=hash_password(payload.password),
                role=payload.role, resident_id=payload.resident_id)
    db.add(user); db.commit(); db.refresh(user)
    return TokenResponse(access_token=create_access_token(user))


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter_by(username=payload.username).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")
    return TokenResponse(access_token=create_access_token(user))
