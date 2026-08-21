from __future__ import annotations

import csv
import os
import tempfile
import zipfile
from datetime import date
from pathlib import Path
from types import SimpleNamespace

os.environ.setdefault("FLIX_GTFS_DIR", "/tmp/fareweave-test-gtfs")

from reisevergleich.gtfs_flix import (
    _build_database, _search_sync, enrich_live_prices, gtfs_local_datetime,
    gtfs_seconds, service_active, stop_score,
)


assert gtfs_seconds("24:15:00") == 87300
assert gtfs_seconds("25:05:00") == 90300
for invalid in ("", "12:70:00", "-1:00:00"):
    try:
        gtfs_seconds(invalid)
        raise AssertionError(f"{invalid!r} hätte abgelehnt werden müssen")
    except ValueError:
        pass

regular = {day: "0" for day in ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")}
regular.update({"monday": "1", "start_date": "20260801", "end_date": "20260831"})
assert service_active(regular, {}, date(2026, 8, 24))
assert not service_active(regular, {}, date(2026, 8, 25))
assert service_active(regular, {"20260825": 1}, date(2026, 8, 25))
assert not service_active(regular, {"20260824": 2}, date(2026, 8, 24))
assert not service_active(None, {}, date(2026, 8, 24))
assert service_active(None, {"20260824": 1}, date(2026, 8, 24))
assert stop_score("Leipzig Hbf", "Leipzig central train station") >= 75
assert stop_score("BERLIN", "Berlin central bus station") >= 75
assert stop_score("Frankfurt", "Frankfurt am Main Hbf") >= 75
assert stop_score("Dortmund", "Dresden") == 0

# Transitous' Flix feed uses UTC stop_times. Conversion to Europe/Berlin must
# follow DST without applying a fixed offset.
assert gtfs_local_datetime(date(2026, 8, 24), gtfs_seconds("09:04:00"), "UTC").isoformat() == "2026-08-24T11:04:00+02:00"
assert gtfs_local_datetime(date(2026, 1, 12), gtfs_seconds("09:04:00"), "UTC").isoformat() == "2026-01-12T10:04:00+01:00"
assert gtfs_local_datetime(date(2026, 8, 24), gtfs_seconds("09:04:00"), "Europe/Berlin").isoformat() == "2026-08-24T09:04:00+02:00"


def csv_bytes(fieldnames, rows):
    import io
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=fieldnames, lineterminator="\n")
    writer.writeheader(); writer.writerows(rows)
    return output.getvalue()


with tempfile.TemporaryDirectory() as temporary:
    root = Path(temporary); archive_path = root / "feed.zip"; database = root / "feed.sqlite3"
    files = {
        "agency.txt": csv_bytes(["agency_id", "agency_name", "agency_timezone"], [
            {"agency_id": "FLIXBUS-eu", "agency_name": "FlixBus", "agency_timezone": "UTC"},
            {"agency_id": "FLIXTRAIN-eu", "agency_name": "FlixTrain", "agency_timezone": "UTC"},
        ]),
        "routes.txt": csv_bytes(["route_id", "agency_id", "route_short_name", "route_long_name", "route_type"], [
            {"route_id": "B", "agency_id": "FLIXBUS-eu", "route_short_name": "N1", "route_long_name": "Bus", "route_type": "3"},
            {"route_id": "T", "agency_id": "FLIXTRAIN-eu", "route_short_name": "FLX1", "route_long_name": "Train", "route_type": "2"},
        ]),
        "trips.txt": csv_bytes(["route_id", "service_id", "trip_id"], [
            {"route_id": "B", "service_id": "regular", "trip_id": "bus"},
            {"route_id": "T", "service_id": "added", "trip_id": "train"},
            {"route_id": "B", "service_id": "removed", "trip_id": "removed"},
            {"route_id": "B", "service_id": "night", "trip_id": "night"},
        ]),
        "stops.txt": csv_bytes(["stop_id", "stop_name", "parent_station", "stop_timezone"], [
            {"stop_id": "L", "stop_name": "Leipzig central train station", "parent_station": "", "stop_timezone": "Europe/Berlin"},
            {"stop_id": "D", "stop_name": "Dortmund Central Station", "parent_station": "", "stop_timezone": "Europe/Berlin"},
        ]),
        "stop_times.txt": csv_bytes(["trip_id", "arrival_time", "departure_time", "stop_id", "stop_sequence"], [
            {"trip_id": trip, "arrival_time": dep, "departure_time": dep, "stop_id": "L", "stop_sequence": "1"}
            for trip, dep in (("bus", "14:00:00"), ("train", "16:00:00"), ("removed", "18:00:00"), ("night", "24:15:00"))
        ] + [
            {"trip_id": trip, "arrival_time": arr, "departure_time": arr, "stop_id": "D", "stop_sequence": "2"}
            for trip, arr in (("bus", "17:00:00"), ("train", "19:00:00"), ("removed", "21:00:00"), ("night", "25:05:00"))
        ]),
        "calendar.txt": csv_bytes(["service_id", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday", "start_date", "end_date"], [
            {"service_id": service, "monday": "1", "tuesday": "0", "wednesday": "0", "thursday": "0", "friday": "0", "saturday": "0", "sunday": "0", "start_date": "20260801", "end_date": "20260831"}
            for service in ("regular", "removed", "night")
        ]),
        "calendar_dates.txt": csv_bytes(["service_id", "date", "exception_type"], [
            {"service_id": "added", "date": "20260824", "exception_type": "1"},
            {"service_id": "removed", "date": "20260824", "exception_type": "2"},
        ]),
    }
    with zipfile.ZipFile(archive_path, "w") as archive:
        for name, content in files.items(): archive.writestr(name, content)
    _build_database(archive_path, database, {"test": True})
    request = SimpleNamespace(origin="Leipzig Hbf", destination="Dortmund Hbf", travel_date="2026-08-24", departure_after="14:00", include_flixtrain=True, include_flixbus=True, preference="fastest", max_results=24)
    result = _search_sync(database, request)
    assert len(result["routes"]) == 3, result
    assert {route["provider"] for route in result["routes"]} == {"FlixBus", "FlixTrain"}, result
    assert any(route["departure"].startswith("2026-08-25T02:15") for route in result["routes"]), result
    assert all(route["price"] is None and route["deutschlandticket_covered"] is False for route in result["routes"])
    request.departure_after = "17:00"
    later = _search_sync(database, request)
    assert all(route["departure"] >= "2026-08-24T17:00" for route in later["routes"])
    request.include_flixbus = False
    trains = _search_sync(database, request)
    assert all(route["provider"] == "FlixTrain" for route in trains["routes"])

print("gtfs flix: OK")

schedule = {"candidate_routes": [{"departure": "2026-08-24T14:00:00+02:00", "arrival": "2026-08-24T17:00:00+02:00", "flix_kind": "bus", "price": None}], "routes": [{}], "provider_status": {"ok": True}}
live = {"candidate_routes": [{"departure": {"time": "2026-08-24T14:00:00+02:00"}, "arrival": {"time": "2026-08-24T17:00:00+02:00"}, "flix_kind": "bus", "price": 19.99, "currency": "EUR", "booking_url": "https://shop.flixbus.com/search"}], "provider_status": {"ok": True}}
enriched = enrich_live_prices(schedule, live)
assert enriched["candidate_routes"][0]["price"] == 19.99
assert enriched["provider_status"]["live_pricing"]["matched_prices"] == 1

ambiguous = {**live, "candidate_routes": live["candidate_routes"] * 2}
schedule["candidate_routes"][0]["price"] = None
assert enrich_live_prices(schedule, ambiguous)["candidate_routes"][0]["price"] is None

for service_day, gtfs_time, live_time in (
    (date(2026, 8, 24), "09:04:00", "2026-08-24T11:04:00+02:00"),
    (date(2026, 1, 12), "09:04:00", "2026-01-12T10:04:00+01:00"),
):
    normalized = gtfs_local_datetime(service_day, gtfs_seconds(gtfs_time), "UTC").isoformat()
    winter_or_summer_schedule = {
        "candidate_routes": [{"departure": normalized, "arrival": normalized, "flix_kind": "train", "price": None}],
        "routes": [{}], "provider_status": {"ok": True},
    }
    winter_or_summer_live = {
        "candidate_routes": [{"departure": {"time": live_time}, "arrival": {"time": live_time}, "flix_kind": "train", "price": 12.49}],
        "provider_status": {"ok": True},
    }
    matched = enrich_live_prices(winter_or_summer_schedule, winter_or_summer_live)
    assert matched["candidate_routes"][0]["price"] == 12.49, matched
