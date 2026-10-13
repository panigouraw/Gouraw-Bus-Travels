from datetime import date, time, timedelta
from database import SessionLocal
import models

db = SessionLocal()

# Run only once - skip if data already exists
if db.query(models.Bus).count() > 0:
    print("Sample data already exists. Nothing added.")
    db.close()
    raise SystemExit

# ---------- Buses ----------
bus1 = models.Bus(name="Kadapa Express", bus_number="AP04 Z 1001", bus_type="AC Seater", total_seats=40)
bus2 = models.Bus(name="Rayalaseema Travels", bus_number="AP04 Z 2002", bus_type="Non-AC Seater", total_seats=40)
bus3 = models.Bus(name="Night Rider", bus_number="AP04 Z 3003", bus_type="AC Sleeper", total_seats=30)
db.add_all([bus1, bus2, bus3])
db.commit()

# ---------- Stops (name, latitude, longitude) - approximate locations ----------
kadapa_to_tirupati = [
    ("Kadapa", 14.4673, 78.8242),
    ("Vontimitta", 14.3957, 79.0222),
    ("Rajampet", 14.1930, 79.1590),
    ("Railway Koduru", 13.9667, 79.2500),
    ("Renigunta", 13.6393, 79.5140),
    ("Tirupati", 13.6288, 79.4192),
]


def make_route(source, destination, stops):
    route = models.Route(source=source, destination=destination)
    db.add(route)
    db.commit()
    for order, (name, lat, lng) in enumerate(stops, start=1):
        db.add(models.Stop(route_id=route.id, stop_name=name,
                           stop_order=order, latitude=lat, longitude=lng))
    db.commit()
    return route


route1 = make_route("Kadapa", "Tirupati", kadapa_to_tirupati)
route2 = make_route("Tirupati", "Kadapa", list(reversed(kadapa_to_tirupati)))

# ---------- Schedules for the next 7 days ----------
timings = [
    (bus1, time(6, 0), time(10, 30), 250),
    (bus2, time(14, 0), time(18, 30), 180),
    (bus3, time(22, 0), time(2, 30), 400),
]

today = date.today()
for day in range(7):
    journey_date = today + timedelta(days=day)
    for route in (route1, route2):
        for bus, dep, arr, price in timings:
            db.add(models.Schedule(bus_id=bus.id, route_id=route.id,
                                   journey_date=journey_date,
                                   departure_time=dep, arrival_time=arr,
                                   price=price))
db.commit()
db.close()
print("Sample data added successfully")