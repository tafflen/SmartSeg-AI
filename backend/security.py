"""JWT authentication. Token refresh/revocation is a future production hardening step."""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Callable

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from models import User, get_db

SECRET_KEY = os.getenv("JWT_SECRET", os.getenv("SMARTSEG_JWT_SECRET", "change-this-development-secret-before-deployment"))
ALGORITHM = "HS256"
TOKEN_EXPIRY_HOURS = 24
password_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
bearer_scheme = HTTPBearer()


def hash_password(password: str) -> str: return password_context.hash(password)
def verify_password(password: str, password_hash: str) -> bool: return password_context.verify(password, password_hash)


def create_access_token(user: User) -> str:
    expires = datetime.now(timezone.utc) + timedelta(hours=TOKEN_EXPIRY_HOURS)
    return jwt.encode({"sub": str(user.id), "role": user.role, "exp": expires}, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(role_required: str | None = None) -> Callable:
    """Return a FastAPI dependency; use get_current_user('admin') for role protection."""
    def dependency(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme), db: Session = Depends(get_db)) -> User:
        try:
            payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
            user = db.get(User, int(payload.get("sub", "")))
        except (JWTError, ValueError):
            user = None
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
        if role_required and user.role != role_required:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
        return user
    return dependency


def require_roles(*roles: str) -> Callable:
    def dependency(user: User = Depends(get_current_user())) -> User:
        if user.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
        return user
    return dependency
