from __future__ import annotations

from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

Role = Literal["resident", "rwa", "gcc", "admin"]
Category = Literal["PLASTIC", "ORGANIC", "METAL", "OTHER"]


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=8, max_length=128)
    role: Role
    resident_id: int | None = None


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class ResidentCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    nfc_uid: str = Field(min_length=1, max_length=128)
    phone: str | None = Field(default=None, max_length=32)


class ResidentUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    nfc_uid: str | None = Field(default=None, min_length=1, max_length=128)
    phone: str | None = Field(default=None, max_length=32)


class ResidentResponse(ORMModel):
    id: int; name: str; nfc_uid: str; phone: str | None; wallet_balance: float; created_at: str


class WasteEventCreate(BaseModel):
    client_event_uuid: str = Field(min_length=8, max_length=64)
    resident_id: int
    category: Category
    confidence_score: float | None = Field(default=None, ge=0, le=1)
    weight_grams: float | None = Field(default=None, ge=0)
    reward_points: int = Field(default=0, ge=0)
    timestamp: str | None = None


class WasteEventResponse(ORMModel):
    id: int; client_event_uuid: str | None; resident_id: int; category: Category
    confidence_score: float | None; weight_grams: float | None; reward_points: int
    timestamp: str; synced_to_firebase: bool


class NFCScanRequest(BaseModel): nfc_uid: str = Field(min_length=1, max_length=128)
class NFCRegisterRequest(NFCScanRequest): resident_id: int
class NFCScanResponse(BaseModel): resident_id: int; name: str; status: str = "REGISTERED"

class RedeemRequest(BaseModel): points: int = Field(ge=1)
class TransactionResponse(ORMModel):
    id: int; resident_id: int; type: Literal["earn", "redeem"]; points: int; timestamp: str; note: str | None

class SyncQueueResponse(ORMModel):
    id: int; waste_event_id: int; status: str; retry_count: int; last_attempt: str | None
