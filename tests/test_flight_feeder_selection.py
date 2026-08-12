from datetime import datetime
from zoneinfo import ZoneInfo

from reisevergleich.planner import _feeder_probe_options


def option(index: int, departure: str, price: float) -> dict:
    return {
        "provider": "fixture",
        "price": price,
        "outbound": {
            "departure_airport": "AAA",
            "arrival_airport": "BBB",
            "departure": departure,
            "arrival": "2026-09-15T12:00+02:00",
        },
        "return": {
            "departure_airport": "BBB",
            "arrival_airport": "AAA",
            "departure": "2026-09-22T12:00+02:00",
            "arrival": "2026-09-22T15:00+02:00",
        },
        "id": index,
    }


options = [
    option(1, "2026-09-15T06:00+02:00", 100),
    option(2, "2026-09-15T06:15+02:00", 101),
    option(3, "2026-09-15T06:30+02:00", 102),
    option(4, "2026-09-15T09:00+02:00", 120),
]

selected = _feeder_probe_options(
    options,
    travel_date="2026-09-15",
    departure_after="06:00",
    buffer_minutes=120,
    limit=6,
)

assert [item["id"] for item in selected] == [4], selected
print("Flugvorauswahl behält spätere zubringerkompatible Optionen: OK")
