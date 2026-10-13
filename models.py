

from sqlalchemy import (
    Column, Integer, String, Date, Time, DateTime, Numeric,
    ForeignKey, UniqueConstraint, Float
)
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    mobile = Column(String(15), nullable=False)
    password_hash = Column(String(255), nullable=False)   # never store the real password
    created_at = Column(DateTime, default=datetime.utcnow)


class Bus(Base):
    __tablename__ = "buses"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    bus_number = Column(String(20), unique=True, nullable=False)
    bus_type = Column(String(50))
    total_seats = Column(Integer, default=40)


class Route(Base):
    __tablename__ = "routes"

    id = Column(Integer, primary_key=True, index=True)
    source = Column(String(100), nullable=False)
    destination = Column(String(100), nullable=False)

    stops = relationship("Stop", back_populates="route", order_by="Stop.stop_order")


class Stop(Base):
    __tablename__ = "stops"

    id = Column(Integer, primary_key=True, index=True)
    route_id = Column(Integer, ForeignKey("routes.id"), nullable=False)
    stop_name = Column(String(100), nullable=False)
    stop_order = Column(Integer, nullable=False)
    latitude = Column(Float)
    longitude = Column(Float)

    route = relationship("Route", back_populates="stops")


class Schedule(Base):
    __tablename__ = "schedules"

    id = Column(Integer, primary_key=True, index=True)
    bus_id = Column(Integer, ForeignKey("buses.id"), nullable=False)
    route_id = Column(Integer, ForeignKey("routes.id"), nullable=False)
    journey_date = Column(Date, nullable=False)
    departure_time = Column(Time, nullable=False)
    arrival_time = Column(Time, nullable=False)
    price = Column(Numeric(8, 2), nullable=False)

    bus = relationship("Bus")
    route = relationship("Route")


class Booking(Base):
    __tablename__ = "bookings"

    id = Column(Integer, primary_key=True, index=True)
    booking_code = Column(String(20), unique=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    schedule_id = Column(Integer, ForeignKey("schedules.id"), nullable=False)
    email = Column(String(100), nullable=False)
    mobile = Column(String(15), nullable=False)
    total_amount = Column(Numeric(8, 2), nullable=False)
    status = Column(String(20), default="CONFIRMED")       # CONFIRMED / CANCELLED
    created_at = Column(DateTime, default=datetime.utcnow)
    cancelled_at = Column(DateTime, nullable=True)
    refund_amount = Column(Numeric(8, 2), nullable=True)

    user = relationship("User")
    schedule = relationship("Schedule")
    passengers = relationship("Passenger", back_populates="booking")


class Passenger(Base):
    __tablename__ = "passengers"
    # Same seat cannot be active twice for the same schedule.
    # When a booking is cancelled, seat_number becomes NULL (seat is free again)
    # and seat_label keeps the original seat for booking history.
    __table_args__ = (UniqueConstraint("schedule_id", "seat_number", name="uq_schedule_seat"),)

    id = Column(Integer, primary_key=True, index=True)
    booking_id = Column(Integer, ForeignKey("bookings.id"), nullable=False)
    schedule_id = Column(Integer, ForeignKey("schedules.id"), nullable=False)
    name = Column(String(100), nullable=False)
    age = Column(Integer, nullable=False)
    gender = Column(String(10), nullable=False)
    seat_number = Column(String(5), nullable=True)
    seat_label = Column(String(5), nullable=False)
    status = Column(String(10), default="ACTIVE")          # ACTIVE / CANCELLED

    booking = relationship("Booking", back_populates="passengers")


class BusLocation(Base):
    __tablename__ = "bus_locations"

    id = Column(Integer, primary_key=True, index=True)
    schedule_id = Column(Integer, ForeignKey("schedules.id"), unique=True, nullable=False)
    current_stop_id = Column(Integer, ForeignKey("stops.id"))
    latitude = Column(Float)
    longitude = Column(Float)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
