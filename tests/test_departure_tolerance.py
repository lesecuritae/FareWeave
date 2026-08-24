from __future__ import annotations

import asyncio

from reisevergleich import compare
from reisevergleich.config import SEARCH_DEPARTURE_TOLERANCE_MINUTES
from reisevergleich.db import rank_routes
from reisevergleich.models import ReiseRequest, StationSelection
from reisevergleich.utils import annotate_departure_tolerance, departure_search_floor, route_departure_in_window


DATE = "2030-10-27"


def route(identifier: str, time: str, *, source: str = "transitous", operator: str = "LEO Express") -> dict:
    return {
        "id": identifier,
        "provider": "Transitous" if source == "transitous" else source,
        "provider_code": source,
        "db_source": source,
        "type": "train",
        "origin": "Leipzig Hbf",
        "destination": "Frankfurt(Main) Hbf",
        "departure": f"{DATE}T{time}:00+01:00",
        "arrival": f"{DATE}T07:29:00+01:00",
        "duration_minutes": 275,
        "transfers": 1,
        "legs": [{
            "mode": "REGIONAL_RAIL",
            "line": "DRF (232)",
            "operator": operator,
            "provider": operator,
            "origin": {"name": "Leipzig Hbf"},
            "destination": {"name": "Frankfurt (Main) Südbahnhof"},
        }],
    }


def test_window_boundaries_and_priority():
    assert SEARCH_DEPARTURE_TOLERANCE_MINUTES == 15
    assert departure_search_floor(DATE, "03:00") == (DATE, "02:45")
    assert route_departure_in_window(route("le-232", "02:54"), DATE, "03:00", tolerance_minutes=15)
    assert not route_departure_in_window(route("too-early", "02:44"), DATE, "03:00", tolerance_minutes=15)
    next_day = route("next-day", "02:54")
    next_day["departure"] = "2030-10-28T02:54:00+01:00"
    assert not route_departure_in_window(next_day, DATE, "03:00", tolerance_minutes=15)
    international = route("international", "02:50")
    international["destination"] = "Wien Hbf"
    assert route_departure_in_window(international, DATE, "03:00", tolerance_minutes=15)

    ranked = rank_routes([
        annotate_departure_tolerance(route("later", "03:05"), DATE, "03:00"),
        annotate_departure_tolerance(route("early", "02:54"), DATE, "03:00"),
        annotate_departure_tolerance(route("exact", "03:00"), DATE, "03:00"),
    ], "fastest")
    assert [item["id"] for item in ranked] == ["exact", "early", "later"]
    assert ranked[1]["early_departure_minutes"] == 6


def test_compare_queries_all_ground_providers_with_floor_and_keeps_le(monkeypatch):
    observed = {}

    async def fake_db(**kwargs):
        observed["db"] = (kwargs["travel_date"], kwargs["departure_after"])
        observed["db_ids"] = (kwargs.get("origin_id"), kwargs.get("destination_id"))
        return ({"journeys": [route("db-later", "03:10", source="dbnav", operator="DB Fernverkehr AG")], "source": "dbnav"}, [])

    async def fake_transitous(request):
        observed["transitous"] = (request.travel_date, request.departure_after)
        return {"routes": [route("le-232", "02:54")], "diagnostic": {"ok": True, "routes": 1}}

    async def fake_flix(request):
        observed["flix"] = (request.travel_date, request.departure_after)
        return {"routes": [], "candidate_routes": [], "candidate_counts": {}, "provider_status": {"ok": True}}

    async def identity(routes):
        return routes

    monkeypatch.setattr(compare, "db_search_with_retry", fake_db)
    monkeypatch.setattr(compare, "transitous_search", fake_transitous)
    monkeypatch.setattr(compare, "flix_search", fake_flix)
    monkeypatch.setattr(compare, "_enrich_history_bounded", identity)
    request = ReiseRequest(
        origin="Leipzig Hbf",
        destination="Frankfurt(Main) Hbf",
        travel_date=DATE,
        departure_after="03:00",
        max_results=10,
        split_ticket_check=False,
        origin_station=StationSelection(
            name="Leipzig Hbf", provider="db", provider_id="8010205",
            provider_ids={"db":"8010205", "transitous":"leipzig-transitous", "flix":"leipzig-flix"},
        ),
        destination_station=StationSelection(
            name="Frankfurt(Main) Hbf", provider="db", provider_id="8000105",
            provider_ids={"db":"8000105", "transitous":"frankfurt-transitous", "flix":"frankfurt-flix"},
        ),
    )
    result = asyncio.run(compare.compare_trip(request))
    assert observed == {
        "db": (DATE, "02:45"), "db_ids": ("8010205", "8000105"),
        "transitous": (DATE, "02:45"), "flix": (DATE, "02:45"),
    }
    early = next(item for item in result["visible_options"] if item["id"] == "le-232")
    assert early["early_departure_minutes"] == 6
    assert early["legs"][0]["operator"] == "LEO Express"
    assert any(item["id"] == "db-later" for item in result["visible_options"])
    states = {item["provider"]: item["outcome"] for item in result["provider_statuses"]}
    assert states == {"DB": "connection_found", "Transitous": "connection_found", "Flix": "no_connection"}


def test_provider_states_distinguish_empty_and_failure():
    assert compare._provider_state("Flix", ok=True)["outcome"] == "no_connection"
    assert compare._provider_state("Flix", ok=False)["message"] == "Technischer Abruffehler"
    assert compare._provider_state("DB", ok=True, result_count=1)["outcome"] == "connection_found"
