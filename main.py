import random
import string
from datetime import date, datetime
from decimal import Decimal
from typing import List

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

import models
from auth import router as auth_router, get_current_user, get_db
from tracking import router as tracking_router

app = FastAPI(title="Bus Booking API")

# Allows our frontend (HTML/JS/React) to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(tracking_router)


# ---------------------------------------------------------------
# Request formats
# ---------------------------------------------------------------
class PassengerIn(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    age: int = Field(ge=1, le=120)
    gender: str
    seat_number: str

    @field_validator("gender")
    @classmethod
    def check_gender(cls, v):
        v = v.strip().capitalize()
        if v not in ("Male", "Female", "Other"):
            raise ValueError("gender must be Male, Female or Other")
        return v


class BookingIn(BaseModel):
    schedule_id: int
    email: str
    mobile: str
    passengers: List[PassengerIn] = Field(min_length=1, max_length=6)

    @field_validator("email")
    @classmethod
    def check_email(cls, v):
        v = v.strip()
        if "@" not in v or "." not in v.split("@")[-1]:
            raise ValueError("enter a valid email")
        return v

    @field_validator("mobile")
    @classmethod
    def check_mobile(cls, v):
        v = v.strip()
        if not (v.isdigit() and len(v) == 10):
            raise ValueError("mobile must be 10 digits")
        return v


def departure_time_of(schedule: models.Schedule) -> datetime:
    return datetime.combine(schedule.journey_date, schedule.departure_time)


def refund_percent(hours_left: float) -> int:
    if hours_left >= 24:
        return 90
    if hours_left >= 6:
        return 50
    return 0


# ---------------------------------------------------------------
# Home + cities
# ---------------------------------------------------------------
@app.get("/")
def home():
    return {"message": "Bus Booking API is running"}


@app.get("/cities")
def get_cities(db: Session = Depends(get_db)):
    sources = db.query(models.Route.source).distinct().all()
    destinations = db.query(models.Route.destination).distinct().all()
    return sorted({r[0] for r in sources + destinations})


# ---------------------------------------------------------------
# Search buses (buses that already left today are hidden)
# ---------------------------------------------------------------
@app.get("/search")
def search_buses(source: str, destination: str, journey_date: date,
                 db: Session = Depends(get_db)):
    schedules = (
        db.query(models.Schedule)
        .join(models.Route)
        .filter(
            func.lower(models.Route.source) == source.strip().lower(),
            func.lower(models.Route.destination) == destination.strip().lower(),
            models.Schedule.journey_date == journey_date,
        )
        .order_by(models.Schedule.departure_time)
        .all()
    )
    now = datetime.now()
    schedules = [s for s in schedules if departure_time_of(s) > now]

    if not schedules:
        return {"available": False, "message": "Buses not available", "buses": []}

    buses = []
    for s in schedules:
        booked = db.query(models.Passenger).filter(
            models.Passenger.schedule_id == s.id,
            models.Passenger.seat_number.isnot(None),
        ).count()
        buses.append({
            "schedule_id": s.id,
            "bus_name": s.bus.name,
            "bus_type": s.bus.bus_type,
            "departure_time": str(s.departure_time),
            "arrival_time": str(s.arrival_time),
            "price": float(s.price),
            "available_seats": s.bus.total_seats - booked,
        })
    return {"available": True, "message": "Buses found", "buses": buses}


# ---------------------------------------------------------------
# Seats
# ---------------------------------------------------------------
@app.get("/seats/{schedule_id}")
def get_seats(schedule_id: int, db: Session = Depends(get_db)):
    schedule = db.query(models.Schedule).filter(models.Schedule.id == schedule_id).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")

    booked = {
        p.seat_number
        for p in db.query(models.Passenger).filter(
            models.Passenger.schedule_id == schedule_id,
            models.Passenger.seat_number.isnot(None),
        )
    }
    seats = [
        {"seat_number": str(n), "status": "booked" if str(n) in booked else "available"}
        for n in range(1, schedule.bus.total_seats + 1)
    ]
    return {
        "schedule_id": schedule_id,
        "bus_name": schedule.bus.name,
        "price_per_seat": float(schedule.price),
        "total_seats": schedule.bus.total_seats,
        "available_seats": schedule.bus.total_seats - len(booked),
        "seats": seats,
    }


# ---------------------------------------------------------------
# Booking helpers
# ---------------------------------------------------------------
def make_booking_code(db: Session) -> str:
    while True:
        code = "BUS" + "".join(random.choices(string.ascii_uppercase + string.digits, k=8))
        if not db.query(models.Booking).filter(models.Booking.booking_code == code).first():
            return code


def booking_response(booking: models.Booking):
    s = booking.schedule
    hours_left = (departure_time_of(s) - datetime.now()).total_seconds() / 3600
    can_cancel = booking.status == "CONFIRMED" and hours_left > 0
    refund_if_cancelled = (
        float(booking.total_amount * refund_percent(hours_left) / 100) if can_cancel else None
    )
    return {
        "booking_code": booking.booking_code,
        "status": booking.status,
        "bus_name": s.bus.name,
        "bus_type": s.bus.bus_type,
        "schedule_id": s.id,
        "from": s.route.source,
        "to": s.route.destination,
        "journey_date": str(s.journey_date),
        "departure_time": str(s.departure_time),
        "arrival_time": str(s.arrival_time),
        "email": booking.email,
        "mobile": booking.mobile,
        "total_amount": float(booking.total_amount),
        "booked_on": str(booking.created_at),
        "can_cancel": can_cancel,
        "refund_if_cancelled": refund_if_cancelled,
        "refund_amount": float(booking.refund_amount) if booking.refund_amount is not None else None,
        "passengers": [
            {"name": p.name, "age": p.age, "gender": p.gender, "seat_number": p.seat_label}
            for p in booking.passengers
        ],
    }


# ---------------------------------------------------------------
# Book tickets (login required)
# ---------------------------------------------------------------
@app.post("/book")
def book_tickets(data: BookingIn, user: models.User = Depends(get_current_user),
                 db: Session = Depends(get_db)):
    schedule = db.query(models.Schedule).filter(models.Schedule.id == data.schedule_id).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    if departure_time_of(schedule) <= datetime.now():
        raise HTTPException(status_code=400, detail="This bus has already departed")

    seat_numbers = [p.seat_number.strip() for p in data.passengers]
    if len(set(seat_numbers)) != len(seat_numbers):
        raise HTTPException(status_code=400, detail="Same seat selected more than once")

    valid = {str(n) for n in range(1, schedule.bus.total_seats + 1)}
    for seat in seat_numbers:
        if seat not in valid:
            raise HTTPException(status_code=400, detail=f"Seat {seat} does not exist on this bus")

    taken = (
        db.query(models.Passenger.seat_number)
        .filter(models.Passenger.schedule_id == data.schedule_id,
                models.Passenger.seat_number.in_(seat_numbers))
        .all()
    )
    if taken:
        raise HTTPException(status_code=409,
                            detail="Seat already booked: " + ", ".join(t[0] for t in taken))

    try:
        booking = models.Booking(
            booking_code=make_booking_code(db),
            user_id=user.id,
            schedule_id=data.schedule_id,
            email=data.email,
            mobile=data.mobile,
            total_amount=schedule.price * len(data.passengers),
            status="CONFIRMED",
        )
        db.add(booking)
        db.flush()
        for p in data.passengers:
            seat = p.seat_number.strip()
            db.add(models.Passenger(
                booking_id=booking.id,
                schedule_id=data.schedule_id,
                name=p.name.strip(),
                age=p.age,
                gender=p.gender,
                seat_number=seat,
                seat_label=seat,
                status="ACTIVE",
            ))
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Seat just got booked by someone else")

    db.refresh(booking)
    return {"message": "Booking confirmed", "booking": booking_response(booking)}


# ---------------------------------------------------------------
# Booking history, one booking, cancel (login required)
# ---------------------------------------------------------------
@app.get("/my-bookings")
def my_bookings(user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = (
        db.query(models.Booking)
        .filter(models.Booking.user_id == user.id)
        .order_by(models.Booking.created_at.desc())
        .all()
    )
    return {"count": len(rows), "bookings": [booking_response(b) for b in rows]}


def own_booking(db: Session, code: str, user: models.User) -> models.Booking:
    booking = (
        db.query(models.Booking)
        .filter(models.Booking.booking_code == code.upper(),
                models.Booking.user_id == user.id)
        .first()
    )
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    return booking


@app.get("/booking/{booking_code}")
def get_booking(booking_code: str, user: models.User = Depends(get_current_user),
                db: Session = Depends(get_db)):
    return booking_response(own_booking(db, booking_code, user))


@app.post("/booking/{booking_code}/cancel")
def cancel_booking(booking_code: str, user: models.User = Depends(get_current_user),
                   db: Session = Depends(get_db)):
    booking = own_booking(db, booking_code, user)
    if booking.status != "CONFIRMED":
        raise HTTPException(status_code=400, detail="This booking is already cancelled")

    hours_left = (departure_time_of(booking.schedule) - datetime.now()).total_seconds() / 3600
    if hours_left <= 0:
        raise HTTPException(status_code=400, detail="The bus has already departed, so this booking cannot be cancelled")

    percent = refund_percent(hours_left)
    booking.status = "CANCELLED"
    booking.cancelled_at = datetime.utcnow()
    booking.refund_amount = (booking.total_amount * percent / 100).quantize(Decimal("0.01"))
    for p in booking.passengers:
        p.status = "CANCELLED"
        p.seat_number = None  # frees the seat for other people
    db.commit()
    db.refresh(booking)

    return {
        "message": f"Booking cancelled. Refund: {percent}% (Rs. {booking.refund_amount})",
        "booking": booking_response(booking),
    }