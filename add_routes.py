from datetime import date, time, timedelta
from database import SessionLocal
import models

DAYS = 30  # how many days ahead to create schedules

# (stop name, latitude, longitude) - approximate locations
STOPS = {
    "Kadapa-Tirupati": [
        ("Kadapa", 14.4673, 78.8242), ("Vontimitta", 14.3957, 79.0222),
        ("Rajampet", 14.1930, 79.1590), ("Railway Koduru", 13.9667, 79.2500),
        ("Renigunta", 13.6393, 79.5140), ("Tirupati", 13.6288, 79.4192),
    ],
    "Kadapa-Bengaluru": [
        ("Kadapa", 14.4673, 78.8242), ("Rayachoti", 14.0570, 78.7510),
        ("Madanapalle", 13.5503, 78.5029), ("Mulbagal", 13.1637, 78.3946),
        ("Kolar", 13.1357, 78.1294), ("Bengaluru", 12.9716, 77.5946),
    ],
    "Kadapa-Hyderabad": [
        ("Kadapa", 14.4673, 78.8242), ("Nandyal", 15.4786, 78.4836),
        ("Kurnool", 15.8281, 78.0373), ("Jadcherla", 16.7667, 78.1333),
        ("Hyderabad", 17.3850, 78.4867),
    ],
    "Tirupati-Chennai": [
        ("Tirupati", 13.6288, 79.4192), ("Puttur", 13.4410, 79.5560),
        ("Nagari", 13.3240, 79.5860), ("Tiruttani", 13.1810, 79.6120),
        ("Thiruvallur", 13.1430, 79.9080), ("Chennai", 13.0827, 80.2707),
    ],
    "Tirupati-Bengaluru": [
        ("Tirupati", 13.6288, 79.4192), ("Chittoor", 13.2172, 79.1003),
        ("Palamaner", 13.2000, 78.7500), ("Kolar", 13.1357, 78.1294),
        ("Bengaluru", 12.9716, 77.5946),
    ],
}

# Each route pair runs in both directions with the same trips.
# trip = (bus name, bus number, bus type, seats, departure, arrival, price)
PAIRS = [
    ("Kadapa-Tirupati", [
        ("Kadapa Express", "AP04 Z 1001", "AC Seater", 40, time(6, 0), time(10, 30), 250),
        ("Rayalaseema Travels", "AP04 Z 2002", "Non-AC Seater", 40, time(14, 0), time(18, 30), 180),
        ("Night Rider", "AP04 Z 3003", "AC Sleeper", 30, time(22, 0), time(2, 30), 400),
    ]),
    ("Kadapa-Bengaluru", [
        ("Silicon Express", "AP04 Z 4001", "AC Seater", 40, time(7, 0), time(14, 0), 550),
        ("Garden City Sleeper", "AP04 Z 4002", "AC Sleeper", 30, time(21, 30), time(4, 30), 750),
    ]),
    ("Kadapa-Hyderabad", [
        ("Nizam Express", "AP04 Z 5001", "AC Seater", 40, time(8, 0), time(16, 30), 650),
        ("Charminar Sleeper", "AP04 Z 5002", "AC Sleeper", 30, time(21, 0), time(5, 30), 850),
    ]),
    ("Tirupati-Chennai", [
        ("Venkatadri Express", "AP04 Z 6001", "AC Seater", 40, time(6, 30), time(10, 0), 300),
        ("Marina Travels", "AP04 Z 6002", "Non-AC Seater", 40, time(16, 0), time(19, 30), 220),
    ]),
    ("Tirupati-Bengaluru", [
        ("Hills Express", "AP04 Z 7001", "AC Seater", 40, time(7, 30), time(12, 30), 450),
        ("Namma Night Bus", "AP04 Z 7002", "AC Sleeper", 30, time(22, 30), time(4, 0), 650),
    ]),
]

db = SessionLocal()
added_routes = added_schedules = 0


def get_bus(name, number, btype, seats):
    bus = db.query(models.Bus).filter(models.Bus.bus_number == number).first()
    if not bus:
        bus = models.Bus(name=name, bus_number=number, bus_type=btype, total_seats=seats)
        db.add(bus)
        db.commit()
    return bus


def get_route(source, destination, stops):
    global added_routes
    route = db.query(models.Route).filter(
        models.Route.source == source, models.Route.destination == destination
    ).first()
    if not route:
        route = models.Route(source=source, destination=destination)
        db.add(route)
        db.commit()
        for order, (name, lat, lng) in enumerate(stops, start=1):
            db.add(models.Stop(route_id=route.id, stop_name=name,
                               stop_order=order, latitude=lat, longitude=lng))
        db.commit()
        added_routes += 1
    return route


today = date.today()
for key, trips in PAIRS:
    stops = STOPS[key]
    source, destination = stops[0][0], stops[-1][0]
    for src, dst, stop_list in ((source, destination, stops),
                                (destination, source, list(reversed(stops)))):
        route = get_route(src, dst, stop_list)
        for name, number, btype, seats, dep, arr, price in trips:
            bus = get_bus(name, number, btype, seats)
            for d in range(DAYS):
                day = today + timedelta(days=d)
                exists = db.query(models.Schedule).filter(
                    models.Schedule.bus_id == bus.id,
                    models.Schedule.route_id == route.id,
                    models.Schedule.journey_date == day,
                ).first()
                if not exists:
                    db.add(models.Schedule(bus_id=bus.id, route_id=route.id,
                                           journey_date=day, departure_time=dep,
                                           arrival_time=arr, price=price))
                    added_schedules += 1
        db.commit()

db.close()
print(f"Done. New routes: {added_routes}, new schedules: {added_schedules}")