from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import SessionLocal
import models

router = APIRouter(prefix="/track", tags=["Live Tracking"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_schedule_and_stops(db: Session, schedule_id: int):
    schedule = db.query(models.Schedule).filter(models.Schedule.id == schedule_id).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    stops = (
        db.query(models.Stop)
        .filter(models.Stop.route_id == schedule.route_id)
        .order_by(models.Stop.stop_order)
        .all()
    )
    return schedule, stops


def build_tracking(schedule, stops, location):
    """Mark every stop as passed / current / upcoming."""
    current_order = 0
    current_stop = None
    if location and location.current_stop_id:
        for s in stops:
            if s.id == location.current_stop_id:
                current_stop = s
                current_order = s.stop_order

    stop_list = []
    for s in stops:
        if current_stop is None:
            status = "upcoming"
        elif s.stop_order < current_order:
            status = "passed"
        elif s.stop_order == current_order:
            status = "current"
        else:
            status = "upcoming"
        stop_list.append({
            "stop_name": s.stop_name,
            "stop_order": s.stop_order,
            "latitude": s.latitude,
            "longitude": s.longitude,
            "status": status,
        })

    if current_stop is None:
        return {
            "schedule_id": schedule.id,
            "bus_name": schedule.bus.name,
            "started": False,
            "message": "Bus has not started yet",
            "stops": stop_list,
        }

    next_stop = next((s for s in stops if s.stop_order == current_order + 1), None)
    reached = next_stop is None

    return {
        "schedule_id": schedule.id,
        "bus_name": schedule.bus.name,
        "started": True,
        "message": "Bus reached destination" if reached else f"Bus is at {current_stop.stop_name}",
        "current_stop": current_stop.stop_name,
        "next_stop": None if reached else next_stop.stop_name,
        "latitude": location.latitude,
        "longitude": location.longitude,
        "updated_at": str(location.updated_at),
        "stops": stop_list,
    }


# ---------------------------------------------------------------
# 1. Where is my bus now?
# ---------------------------------------------------------------
@router.get("/{schedule_id}")
def track_bus(schedule_id: int, db: Session = Depends(get_db)):
    schedule, stops = get_schedule_and_stops(db, schedule_id)
    location = (
        db.query(models.BusLocation)
        .filter(models.BusLocation.schedule_id == schedule_id)
        .first()
    )
    return build_tracking(schedule, stops, location)


# ---------------------------------------------------------------
# 2. Move the bus to the next stop (demo / driver update)
# ---------------------------------------------------------------
@router.post("/{schedule_id}/next")
def move_to_next_stop(schedule_id: int, db: Session = Depends(get_db)):
    schedule, stops = get_schedule_and_stops(db, schedule_id)
    if not stops:
        raise HTTPException(status_code=400, detail="This route has no stops")

    location = (
        db.query(models.BusLocation)
        .filter(models.BusLocation.schedule_id == schedule_id)
        .first()
    )

    if location is None:
        # bus starts from the first stop
        first = stops[0]
        location = models.BusLocation(
            schedule_id=schedule_id,
            current_stop_id=first.id,
            latitude=first.latitude,
            longitude=first.longitude,
        )
        db.add(location)
    else:
        index = next((i for i, s in enumerate(stops) if s.id == location.current_stop_id), -1)
        if index < len(stops) - 1:
            nxt = stops[index + 1]
            location.current_stop_id = nxt.id
            location.latitude = nxt.latitude
            location.longitude = nxt.longitude

    db.commit()
    db.refresh(location)
    return build_tracking(schedule, stops, location)


# ---------------------------------------------------------------
# 3. Reset tracking (start demo again)
# ---------------------------------------------------------------
@router.post("/{schedule_id}/reset")
def reset_tracking(schedule_id: int, db: Session = Depends(get_db)):
    schedule, stops = get_schedule_and_stops(db, schedule_id)
    db.query(models.BusLocation).filter(
        models.BusLocation.schedule_id == schedule_id
    ).delete()
    db.commit()
    return build_tracking(schedule, stops, None)