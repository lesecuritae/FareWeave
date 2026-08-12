import asyncio
from datetime import datetime

import reisevergleich.feeder as feeder
import reisevergleich.feeder_db as feeder_db
from reisevergleich.presentation import _feeder


def paid_option(departure: str, destination: str) -> dict:
    day = departure[:10]
    return {
        "type": "db_via_split",
        "label": "Zwei separat gesuchte DB-Tickets über einen Übergabebahnhof",
        "departure": departure,
        "arrival": f"{day}T07:24:00+02:00",
        "duration_minutes": 66,
        "total_price": 6.0,
        "price_known": True,
        "currency": "EUR",
        "requires_deutschlandticket": False,
        "self_managed_transfers": 1,
        "split_station": "Rudow (U), Berlin",
        "segments": [
            {
                "provider": "Deutsche Bahn",
                "type": "train",
                "origin": "Berlin Hbf",
                "destination": "Rudow (U), Berlin",
                "departure": departure,
                "arrival": f"{day}T06:53:00+02:00",
                "duration_minutes": 35,
                "price": 2.5,
                "currency": "EUR",
                "legs": [],
            },
            {
                "provider": "Deutsche Bahn",
                "type": "bus",
                "origin": "Rudow (U), Berlin",
                "destination": destination,
                "departure": f"{day}T07:17:00+02:00",
                "arrival": f"{day}T07:24:00+02:00",
                "duration_minutes": 7,
                "price": 3.5,
                "currency": "EUR",
                "legs": [],
            },
        ],
    }


async def check_outbound_regression() -> None:
    original = {
        "_db_routes": feeder._db_routes,
        "_native_split_options": feeder._native_split_options,
        "_feeder_handoffs": feeder._feeder_handoffs,
        "_flix_outbound_feeder_options": feeder._flix_outbound_feeder_options,
        "transitous_search": feeder.transitous_search,
    }
    paid_direct = {
        "provider": "Deutsche Bahn",
        "type": "train",
        "origin": "Berlin Hbf",
        "destination": "Flughafen BER - Terminal 1-2",
        "departure": "2030-09-15T07:00:00+02:00",
        "arrival": "2030-09-15T07:40:00+02:00",
        "duration_minutes": 40,
        "price": 12.0,
        "currency": "EUR",
        "legs": [],
    }
    invalid_split = paid_option(
        "2030-09-15T00:18:00+02:00",
        "Flughafen BER - Terminal 5 [Bus Terminal], Schönefeld",
    )
    late_split = paid_option(
        "2030-09-15T11:20:00+02:00",
        "Flughafen BER - Terminal 1-2",
    )
    late_split["arrival"] = "2030-09-15T12:30:00+02:00"
    dticket_route = {
        "provider": "Transitous",
        "provider_code": "transitous",
        "db_source": "transitous",
        "type": "public_transport",
        "origin": "Berlin Hbf",
        "destination": "Flughafen BER - Terminal 1-2",
        "departure": "2030-09-15T06:30:00+02:00",
        "arrival": "2030-09-15T07:20:00+02:00",
        "duration_minutes": 50,
        "transfers": 0,
        "price": 0,
        "currency": "EUR",
        "legs": [],
    }

    async def fake_db_routes(origin, destination, travel_date, departure_after, **kwargs):
        if kwargs.get("mode") == "deutschlandticket":
            return [], [], "test"
        return [paid_direct], [], "test"

    async def fake_native_split_options(routes):
        return [invalid_split, late_split]

    async def fake_flix(*args, **kwargs):
        return [], {"tested": True}

    async def fake_transitous(request, *, deutschlandticket_only=False):
        assert deutschlandticket_only is True
        return {
            "routes": [dticket_route],
            "diagnostic": {"ok": True, "source": "transitous", "routes": 1},
        }

    try:
        feeder._db_routes = fake_db_routes
        feeder._native_split_options = fake_native_split_options
        feeder._feeder_handoffs = lambda *args, **kwargs: []
        feeder._flix_outbound_feeder_options = fake_flix
        feeder.transitous_search = fake_transitous
        result = await feeder.feeder_outbound(
            "Berlin Hbf",
            "BER",
            "Flughafen BER - Terminal 1-2",
            "2030-09-15",
            "06:00",
            datetime.fromisoformat("2030-09-15T13:45:00+02:00"),
            120,
            preference="dticket_first",
            deutschlandticket_available=True,
            split_ticket_check=True,
            include_flixbus=True,
            include_flixtrain=True,
        )
    finally:
        feeder._db_routes = original["_db_routes"]
        feeder._native_split_options = original["_native_split_options"]
        feeder._feeder_handoffs = original["_feeder_handoffs"]
        feeder._flix_outbound_feeder_options = original["_flix_outbound_feeder_options"]
        feeder.transitous_search = original["transitous_search"]

    options = []
    if isinstance(result.get("selected_option"), dict):
        options.append(result["selected_option"])
    options.extend(x for x in (result.get("alternatives") or []) if isinstance(x, dict))

    assert options, result
    assert any(o.get("requires_deutschlandticket") is True for o in options), result
    assert any(o.get("requires_deutschlandticket") is not True for o in options), result

    lower = datetime.fromisoformat("2030-09-15T06:00:00+02:00")
    cutoff = datetime.fromisoformat("2030-09-15T11:45:00+02:00")
    for option in options:
        dep = datetime.fromisoformat(option["departure"])
        arr = datetime.fromisoformat(option["arrival"])
        assert dep >= lower, option
        assert arr <= cutoff, option
        segments = [x for x in (option.get("segments") or []) if isinstance(x, dict)]
        final_destination = str(segments[-1].get("destination") or "") if segments else ""
        assert "terminal 5" not in final_destination.casefold(), option

    public = _feeder(result)
    views = (public or {}).get("views") or {}
    dticket_view = views.get("deutschlandticket") or {}
    assert dticket_view.get("type") == "deutschlandticket_transitous", views
    assert dticket_view.get("requires_deutschlandticket") is True, dticket_view
    assert dticket_view.get("deutschlandticket_tariff_guaranteed") is False, dticket_view




def check_missing_dticket_view_is_explicit() -> None:
    component = {
        "status": "ok",
        "direction": "home_to_airport",
        "airport_station": "Flughafen BER - Terminal 1-2",
        "deutschlandticket_considered": True,
        "selected_option": paid_option(
            "2030-09-15T06:18:00+02:00",
            "Flughafen BER - Terminal 1-2",
        ),
        "alternatives": [],
    }
    public = _feeder(component)
    view = ((public or {}).get("views") or {}).get("deutschlandticket") or {}
    assert view.get("status") == "unavailable", view
    assert view.get("requires_deutschlandticket") is True, view
    assert view.get("manual_required") is True, view

async def check_native_split_timestamps() -> None:
    original = feeder_db.db_split_analysis

    async def fake_split(token):
        return {
            "status": "success",
            "original_price": 20.0,
            "currency": "EUR",
            "split_options": [
                {
                    "total_price": 12.0,
                    "currency": "EUR",
                    "split_station": {"name": "Berlin Ostkreuz"},
                    "segments": [],
                }
            ],
        }

    route = {
        "provider": "Deutsche Bahn",
        "type": "train",
        "origin": "Berlin Hbf",
        "destination": "Flughafen BER - Terminal 1-2",
        "departure": "2030-09-15T06:18:00+02:00",
        "arrival": "2030-09-15T07:00:00+02:00",
        "duration_minutes": 42,
        "price": 20.0,
        "currency": "EUR",
        "analysis_token": "regression-token",
        "legs": [],
    }
    try:
        feeder_db.db_split_analysis = fake_split
        options = await feeder_db._native_split_options([route])
    finally:
        feeder_db.db_split_analysis = original

    assert options, options
    assert options[0]["departure"].startswith("2030-09-15T06:18"), options[0]
    assert options[0]["arrival"].startswith("2030-09-15T07:00"), options[0]


check_missing_dticket_view_is_explicit()
asyncio.run(check_outbound_regression())
asyncio.run(check_native_split_timestamps())
print("D-Ticket/BER-Zubringer + Split-Zeitstempel Regression: OK")
