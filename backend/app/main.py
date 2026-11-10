"""Weye reservation API — prototype with deterministic booking rules."""
from datetime import date, datetime, timezone
from decimal import Decimal
from os import getenv
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import FileResponse
from pathlib import Path
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import Date, DateTime, ForeignKey, Integer, Numeric, String, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

DATABASE_URL = getenv("DATABASE_URL", "sqlite:///./weye.db")
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {})
SessionLocal = sessionmaker(bind=engine)

class Base(DeclarativeBase):
    pass

class RoomType(Base):
    __tablename__ = "room_types"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    capacity: Mapped[int] = mapped_column(Integer)
    total_rooms: Mapped[int] = mapped_column(Integer)
    nightly_rate: Mapped[Decimal] = mapped_column(Numeric(12, 2))

class Reservation(Base):
    __tablename__ = "reservations"
    id: Mapped[int] = mapped_column(primary_key=True)
    reference: Mapped[str] = mapped_column(String(40), unique=True)
    idempotency_key: Mapped[str] = mapped_column(String(100), unique=True)
    room_type_id: Mapped[int] = mapped_column(ForeignKey("room_types.id"))
    guest_name: Mapped[str] = mapped_column(String(150))
    check_in: Mapped[date] = mapped_column(Date)
    check_out: Mapped[date] = mapped_column(Date)
    guests: Mapped[int] = mapped_column(Integer)
    total_price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    status: Mapped[str] = mapped_column(String(30), default="confirmed")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class Stay(BaseModel):
    check_in: date
    check_out: date
    guests: int = Field(ge=1, le=20)

    @model_validator(mode="after")
    def validate_dates(self):
        # Require a future stay and a positive number of nights.
        if self.check_in < date.today() or self.check_out <= self.check_in:
            raise ValueError("Stay dates must be current/future and check-out after check-in")
        return self

class BookingRequest(Stay):
    room_type_id: int
    guest_name: str = Field(min_length=2, max_length=150)
    idempotency_key: str = Field(min_length=8, max_length=100)

app = FastAPI(title="Weye AI Reservation API", version="0.1.0")

def get_db():
    # Close database sessions after each request.
    with SessionLocal() as session:
        yield session

def available_count(db: Session, room: RoomType, stay: Stay) -> int:
    # Overlapping intervals use half-open [check_in, check_out) semantics.
    booked = db.scalars(select(Reservation).where(Reservation.room_type_id == room.id, Reservation.status == "confirmed", Reservation.check_in < stay.check_out, Reservation.check_out > stay.check_in)).all()
    return room.total_rooms - len(booked)

@app.on_event("startup")
def initialize():
    # Seed demonstration inventory; replace with migrations before production.
    Base.metadata.create_all(engine)
    with SessionLocal.begin() as db:
        if not db.scalar(select(RoomType.id).limit(1)):
            db.add_all([RoomType(name="Standard Double", capacity=2, total_rooms=3, nightly_rate=Decimal("3500.00")), RoomType(name="Deluxe Twin", capacity=2, total_rooms=2, nightly_rate=Decimal("5200.00")), RoomType(name="Family Suite", capacity=4, total_rooms=1, nightly_rate=Decimal("8500.00"))])

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/availability")
def availability(stay: Stay, db: Session = Depends(get_db)):
    # Quote only room types that fit the guest count and have inventory.
    nights = (stay.check_out - stay.check_in).days
    return {"currency": "ETB", "nights": nights, "rooms": [{"room_type_id": r.id, "name": r.name, "available": available_count(db, r, stay), "total_price": str(r.nightly_rate * nights)} for r in db.scalars(select(RoomType)).all() if r.capacity >= stay.guests and available_count(db, r, stay) > 0], "note": "Demo rates; taxes and fees not modeled"}

@app.post("/reservations", status_code=201)
def book(request: BookingRequest, db: Session = Depends(get_db)):
    # Idempotency prevents repeated identical requests from duplicating a booking.
    existing = db.scalar(select(Reservation).where(Reservation.idempotency_key == request.idempotency_key))
    if existing:
        if (existing.room_type_id, existing.guest_name, existing.check_in, existing.check_out, existing.guests) != (request.room_type_id, request.guest_name, request.check_in, request.check_out, request.guests):
            raise HTTPException(409, "Idempotency key reused with different booking details")
        return {"reference": existing.reference, "status": existing.status, "total_price": str(existing.total_price), "currency": "ETB"}
    # Lock the inventory row in PostgreSQL to serialize concurrent reservations.
    # SQLite ignores FOR UPDATE; use PostgreSQL for any concurrency testing.
    room = db.scalar(select(RoomType).where(RoomType.id == request.room_type_id).with_for_update())
    if not room:
        raise HTTPException(404, "Room type not found")
    if request.guests > room.capacity or available_count(db, room, request) < 1:
        raise HTTPException(409, "Room unavailable for selected dates or guest count")
    total = room.nightly_rate * (request.check_out - request.check_in).days
    reservation = Reservation(reference="WEYE-" + uuid4().hex[:10].upper(), idempotency_key=request.idempotency_key, room_type_id=room.id, guest_name=request.guest_name, check_in=request.check_in, check_out=request.check_out, guests=request.guests, total_price=total, status="confirmed")
    db.add(reservation)
    db.commit()
    return {"reference": reservation.reference, "status": reservation.status, "total_price": str(total), "currency": "ETB"}

@app.get("/reservations/{reference}")
def get_reservation(reference: str, db: Session = Depends(get_db)):
    # Demo endpoint only: production must authenticate and authorize access.
    reservation = db.scalar(select(Reservation).where(Reservation.reference == reference))
    if not reservation:
        raise HTTPException(404, "Reservation not found")
    return {"reference": reservation.reference, "guest_name": reservation.guest_name, "check_in": reservation.check_in, "check_out": reservation.check_out, "status": reservation.status, "total_price": str(reservation.total_price), "currency": "ETB"}

@app.get("/demo", include_in_schema=False)
def demo():
    # Serve a standalone browser demo from the backend image.
    return FileResponse(Path(__file__).parent / "static" / "index.html")
