"""
Generates demo bus data for major Indian cities.

For every pair of cities within MAX_KM of each other it creates:
  - routes in both directions, with intermediate stops (other cities on the way)
  - 2 buses per pair (day + night/evening)
  - schedules for the next DAYS days

Safe to run again: nothing is duplicated, and new dates are added.
NOTE: this is generated demo data, not real operator timetables.
"""
import math
from datetime import date, datetime, time, timedelta

DAYS = 7          # days ahead to create schedules for
MAX_KM = 600      # longest straight-line distance for a direct route
ROAD_FACTOR = 1.25  # straight line -> approx road distance

# Add new cities at the END of this list only (bus numbers depend on position)
CITIES = [
    ("Delhi", 28.6139, 77.2090), ("Mumbai", 19.0760, 72.8777),
    ("Bengaluru", 12.9716, 77.5946), ("Chennai", 13.0827, 80.2707),
    ("Hyderabad", 17.3850, 78.4867), ("Kolkata", 22.5726, 88.3639),
    ("Pune", 18.5204, 73.8567), ("Ahmedabad", 23.0225, 72.5714),
    ("Jaipur", 26.9124, 75.7873), ("Lucknow", 26.8467, 80.9462),
    ("Kanpur", 26.4499, 80.3319), ("Nagpur", 21.1458, 79.0882),
    ("Indore", 22.7196, 75.8577), ("Bhopal", 23.2599, 77.4126),
    ("Surat", 21.1702, 72.8311), ("Vadodara", 22.3072, 73.1812),
    ("Visakhapatnam", 17.6868, 83.2185), ("Vijayawada", 16.5062, 80.6480),
    ("Guntur", 16.3067, 80.4365), ("Tirupati", 13.6288, 79.4192),
    ("Kadapa", 14.4673, 78.8242), ("Kurnool", 15.8281, 78.0373),
    ("Anantapur", 14.6819, 77.6006), ("Nellore", 14.4426, 79.9865),
    ("Coimbatore", 11.0168, 76.9558), ("Madurai", 9.9252, 78.1198),
    ("Tiruchirappalli", 10.7905, 78.7047), ("Salem", 11.6643, 78.1460),
    ("Kochi", 9.9312, 76.2673), ("Thiruvananthapuram", 8.5241, 76.9366),
    ("Mysuru", 12.2958, 76.6394), ("Mangaluru", 12.9141, 74.8560),
    ("Hubballi", 15.3647, 75.1240), ("Belagavi", 15.8497, 74.4977),
    ("Panaji", 15.4909, 73.8278), ("Warangal", 17.9689, 79.5941),
    ("Rajahmundry", 17.0005, 81.8040), ("Chandigarh", 30.7333, 76.7794),
    ("Amritsar", 31.6340, 74.8723), ("Ludhiana", 30.9010, 75.8573),
    ("Agra", 27.1767, 78.0081), ("Varanasi", 25.3176, 82.9739),
    ("Patna", 25.5941, 85.1376), ("Ranchi", 23.3441, 85.3096),
    ("Bhubaneswar", 20.2961, 85.8245), ("Raipur", 21.2514, 81.6296),
    ("Jodhpur", 26.2389, 73.0243), ("Udaipur", 24.5854, 73.7125),
    ("Nashik", 19.9975, 73.7898), ("Kolhapur", 16.7050, 74.2433),
    ("Dehradun", 30.3165, 78.0322), ("Guwahati", 26.1445, 91.7362),
    ("Vellore", 12.9165, 79.1325), ("Madanapalle", 13.5503, 78.5029),
]


def km(a, b):
    """Straight-line distance between two cities (haversine)."""
    (_, la1, lo1), (_, la2, lo2) = a, b
    p1, p2 = math.radians(la1), math.radians(la2)
    dp, dl = p2 - p1, math.radians(lo2 - lo1)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 6371 * 2 * math.asin(math.sqrt(h))


def stops_between(a, b):
    """Start city, up to 5 cities lying on the way, end city."""
    d = km(a, b)
    mids = [c for c in CITIES
            if c[0] not in (a[0], b[0]) and km(a, c) + km(c, b) <= d * 1.06]
    mids.sort(key=lambda c: km(a, c))
    if len(mids) > 5:
        picks = sorted({round(i * (len(mids) - 1) / 4) for i in range(5)})
        mids = [mids[i] for i in picks]
    return [a] + mids + [b]


def trips_for(road_km):
    """(code, bus type, seats, departure time, price) for each trip of a pair."""
    seater = max(120, round(road_km * 1.1 / 10) * 10)
    if road_km >= 300:
        sleeper = round(road_km * 1.6 / 10) * 10
        return [("D", "AC Seater", 40, time(6, 0), seater),
                ("N", "AC Sleeper", 30, time(21, 0), sleeper)]
    return [("D", "Non-AC Seater", 40, time(7, 0), seater),
            ("E", "AC Seater", 40, time(16, 0), round(seater * 1.2 / 10) * 10)]


def main():
    from database import SessionLocal
    import models

    db = SessionLocal()
    today = date.today()

    routes = {(r.source, r.destination): r for r in db.query(models.Route)}
    buses = {b.bus_number: b for b in db.query(models.Bus)}
    have = {(s.bus_id, s.route_id, s.journey_date)
            for s in db.query(models.Schedule.bus_id, models.Schedule.route_id,
                              models.Schedule.journey_date)
            .filter(models.Schedule.journey_date >= today)}

    new_routes = new_buses = new_sched = 0

    for i in range(len(CITIES)):
        for j in range(i + 1, len(CITIES)):
            a, b = CITIES[i], CITIES[j]
            if km(a, b) > MAX_KM:
                continue
            road_km = km(a, b) * ROAD_FACTOR
            hours = road_km / 48
            stops = stops_between(a, b)

            for src, dst, stop_list in ((a, b, stops), (b, a, stops[::-1])):
                route = routes.get((src[0], dst[0]))
                if route is None:
                    route = models.Route(source=src[0], destination=dst[0])
                    db.add(route)
                    db.flush()
                    for order, (name, lat, lng) in enumerate(stop_list, start=1):
                        db.add(models.Stop(route_id=route.id, stop_name=name,
                                           stop_order=order, latitude=lat, longitude=lng))
                    routes[(src[0], dst[0])] = route
                    new_routes += 1

                for code, btype, seats, dep, price in trips_for(road_km):
                    number = f"IN{i:02d}{j:02d}-{code}"
                    bus = buses.get(number)
                    if bus is None:
                        kind = "Sleeper" if "Sleeper" in btype else "Express"
                        bus = models.Bus(name=f"{a[0]}-{b[0]} {kind}", bus_number=number,
                                         bus_type=btype, total_seats=seats)
                        db.add(bus)
                        db.flush()
                        buses[number] = bus
                        new_buses += 1
                    arr = (datetime.combine(today, dep) + timedelta(hours=hours)).time()
                    for d in range(DAYS):
                        day = today + timedelta(days=d)
                        if (bus.id, route.id, day) not in have:
                            db.add(models.Schedule(bus_id=bus.id, route_id=route.id,
                                                   journey_date=day, departure_time=dep,
                                                   arrival_time=arr.replace(microsecond=0),
                                                   price=price))
                            have.add((bus.id, route.id, day))
                            new_sched += 1
        db.commit()
        print(f"{CITIES[i][0]} done")

    db.commit()
    db.close()
    print(f"Finished. New routes: {new_routes}, new buses: {new_buses}, new schedules: {new_sched}")


if __name__ == "__main__":
    main()