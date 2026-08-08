"""SQLAlchemy model definitions for the shared SmartSeg SQLite schema."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Generator

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Integer, REAL, String, Text, create_engine, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATABASE_URL = os.getenv("DATABASE_URL", "")
DATABASE_PATH = Path(os.getenv("SMARTSEG_DATABASE_PATH", PROJECT_ROOT / "smartseg.db"))
if DATABASE_URL.startswith("sqlite:///"):
    DATABASE_PATH = Path(DATABASE_URL.removeprefix("sqlite:///"))
if not DATABASE_URL:
    DATABASE_URL = f"sqlite:///{DATABASE_PATH.as_posix()}"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


class Resident(Base):
    __tablename__ = "residents"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    nfc_uid: Mapped[str] = mapped_column(Text, nullable=False, unique=True, index=True)
    phone: Mapped[str | None] = mapped_column(Text)
    wallet_balance: Mapped[float] = mapped_column(REAL, nullable=False, default=0.0)
    created_at: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("CURRENT_TIMESTAMP"))
    events: Mapped[list["WasteEvent"]] = relationship(back_populates="resident")
    user: Mapped["User | None"] = relationship(back_populates="resident", uselist=False)


class User(Base):
    __tablename__ = "users"
    __table_args__ = (CheckConstraint("role IN ('resident', 'rwa', 'gcc', 'admin')"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    role: Mapped[str] = mapped_column(Text, nullable=False)
    resident_id: Mapped[int | None] = mapped_column(ForeignKey("residents.id", ondelete="SET NULL"), unique=True)
    created_at: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("CURRENT_TIMESTAMP"))
    resident: Mapped[Resident | None] = relationship(back_populates="user")


class WasteEvent(Base):
    __tablename__ = "waste_events"
    __table_args__ = (CheckConstraint("category IN ('PLASTIC', 'ORGANIC', 'METAL', 'OTHER')"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    resident_id: Mapped[int] = mapped_column(ForeignKey("residents.id", ondelete="RESTRICT"), nullable=False)
    category: Mapped[str] = mapped_column(Text, nullable=False)
    confidence_score: Mapped[float | None] = mapped_column(REAL)
    weight_grams: Mapped[float | None] = mapped_column(REAL)
    reward_points: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    client_event_uuid: Mapped[str | None] = mapped_column(String, unique=True, index=True)
    timestamp: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("CURRENT_TIMESTAMP"))
    synced_to_firebase: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    resident: Mapped[Resident] = relationship(back_populates="events")
    sync_queue: Mapped["SyncQueue | None"] = relationship(back_populates="waste_event", uselist=False, cascade="all, delete-orphan")


class SyncQueue(Base):
    __tablename__ = "sync_queue"
    __table_args__ = (CheckConstraint("status IN ('pending', 'processing', 'failed', 'synced')"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    waste_event_id: Mapped[int] = mapped_column(ForeignKey("waste_events.id", ondelete="CASCADE"), unique=True, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="pending")
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_attempt: Mapped[str | None] = mapped_column(Text)
    waste_event: Mapped[WasteEvent] = relationship(back_populates="sync_queue")


class Transaction(Base):
    __tablename__ = "transactions"
    __table_args__ = (CheckConstraint("type IN ('earn', 'redeem')"), CheckConstraint("points > 0"))
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    resident_id: Mapped[int] = mapped_column(ForeignKey("residents.id", ondelete="RESTRICT"), nullable=False)
    type: Mapped[str] = mapped_column(Text, nullable=False)
    points: Mapped[int] = mapped_column(Integer, nullable=False)
    timestamp: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("CURRENT_TIMESTAMP"))
    note: Mapped[str | None] = mapped_column(Text)


class BackendEventQueue(Base):
    __tablename__ = "backend_event_queue"
    __table_args__ = (CheckConstraint("status IN ('pending', 'processing', 'failed', 'sent')"), CheckConstraint("retry_count >= 0"))
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    waste_event_id: Mapped[int] = mapped_column(ForeignKey("waste_events.id", ondelete="CASCADE"), unique=True, nullable=False)
    client_event_uuid: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="pending")
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_attempt: Mapped[str | None] = mapped_column(Text)


def get_db() -> Generator:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
