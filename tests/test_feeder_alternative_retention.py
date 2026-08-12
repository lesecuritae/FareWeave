from __future__ import annotations

import asyncio
from datetime import datetime

import reisevergleich.feeder as feeder


def _route(index: int, *, price: float | None, origin: str, destination: str, departure: str, arrival: str) -> dict:
    route = {
        "id": f"r{index}",
        "provider": "Deutsche Bahn",
        "type": "train",
        "origin": origin,
        "destination": destination,
        "departure": departure,
        "arrival": arrival,
        "duration_minutes": 30,
        "currency": "EUR",
        "legs": [
            {
                "mode": "train",
                "line": "FEX",
                "origin": {"name": origin},
                "destination": {"name": destination},
                "departure": departure,
                "arrival": arrival,
            }
        ],
    }
    if price is not None:
        route["price"] = price
    return route


def _outbound_paid_routes() -> list[dict]:
    routes = []
    # Provider order from the real failing run: useful priced results can be
    # behind unpriced rows. The feeder must filter/rank before applying limits.
    for i in range(8):
        routes.append(_route(
            i,
            price=None,
            origin="Berlin Hbf",
            destination="BER Berlin Brandenburg Airport",
            departure=f"2030-09-15T{6 + i//2:02d}:{7 + (i%2)*10:02d}:00+02:00",
            arrival=f"2030-09-15T{6 + i//2:02d}:{28 + (i%2)*10:02d}:00+02:00",
        ))
    for i, price in enumerate((18.90, 21.40, 24.00, 27.50), start=8):
        routes.append(_route(
            i,
            price=price,
            origin="Berlin Hbf",
            destination="BER Berlin Brandenburg Airport",
            departure=f"2030-09-15T{8 + (i-8):02d}:07:00+02:00",
            arrival=f"2030-09-15T{8 + (i-8):02d}:28:00+02:00",
        ))
    return routes


def _return_paid_routes() -> list[dict]:
    routes = []
    for i in range(8):
        routes.append(_route(
            i,
            price=None,
            origin="BER Berlin Brandenburg Airport",
            destination="Berlin Hbf",
            departure=f"2030-09-22T{10 + i//2:02d}:{7 + (i%2)*10:02d}:00+02:00",
            arrival=f"2030-09-22T{10 + i//2:02d}:{37 + (i%2)*10:02d}:00+02:00",
        ))
    for i, price in enumerate((19.90, 22.40, 25.00, 28.50), start=8):
        routes.append(_route(
            i,
            price=price,
            origin="BER Berlin Brandenburg Airport",
            destination="Berlin Hbf",
            departure=f"2030-09-22T{14 + (i-8):02d}:07:00+02:00",
            arrival=f"2030-09-22T{14 + (i-8):02d}:37:00+02:00",
        ))
    return routes


def _dt_routes(origin: str, destination: str, day: str, start_hour: int) -> list[dict]:
    return [
        _route(
            100 + i,
            price=None,
            origin=origin,
            destination=destination,
            departure=f"{day}T{start_hour+i:02d}:07:00+02:00",
            arrival=f"{day}T{start_hour+i:02d}:28:00+02:00",
        )
        for i in range(3)
    ]


async def _no_split(routes):
    return []


async def _no_flix(*args, **kwargs):
    return [], {"tested": True}


async def _run_outbound() -> None:
    original = {
        "_db_routes": feeder._db_routes,
        "_native_split_options": feeder._native_split_options,
        "_feeder_handoffs": feeder._feeder_handoffs,
        "_flix_outbound_feeder_options": feeder._flix_outbound_feeder_options,
    }

    async def fake_db(origin, destination, travel_date, departure_after, *, mode, **kwargs):
        if mode == "deutschlandticket":
            return _dt_routes("Berlin Hbf", "BER Berlin Brandenburg Airport", "2030-09-15", 6), [], "dbnav"
        return _outbound_paid_routes(), [], "dbnav"

    try:
        feeder._db_routes = fake_db
        feeder._native_split_options = _no_split
        feeder._feeder_handoffs = lambda *args, **kwargs: []
        feeder._flix_outbound_feeder_options = _no_flix
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
            include_flixbus=False,
            include_flixtrain=False,
        )
    finally:
        feeder._db_routes = original["_db_routes"]
        feeder._native_split_options = original["_native_split_options"]
        feeder._feeder_handoffs = original["_feeder_handoffs"]
        feeder._flix_outbound_feeder_options = original["_flix_outbound_feeder_options"]

    options = [result.get("selected_option"), *(result.get("alternatives") or [])]
    options = [item for item in options if isinstance(item, dict)]
    assert any(item.get("requires_deutschlandticket") is True for item in options), options
    assert any(item.get("requires_deutschlandticket") is not True and item.get("price_known") is True and float(item.get("total_price") or 0) > 0 for item in options), (
        "Bepreiste DB-Alternativen hinter unbepreisten Providerzeilen wurden verloren: " + repr(options)
    )


async def _run_return() -> None:
    original = {
        "_db_routes": feeder._db_routes,
        "_native_split_options": feeder._native_split_options,
        "_feeder_handoffs": feeder._feeder_handoffs,
        "_flix_return_feeder_options": feeder._flix_return_feeder_options,
    }

    async def fake_db(origin, destination, travel_date, departure_after, *, mode, **kwargs):
        if mode == "deutschlandticket":
            return _dt_routes("BER Berlin Brandenburg Airport", "Berlin Hbf", "2030-09-22", 10), [], "dbnav"
        return _return_paid_routes(), [], "dbnav"

    try:
        feeder._db_routes = fake_db
        feeder._native_split_options = _no_split
        feeder._feeder_handoffs = lambda *args, **kwargs: []
        feeder._flix_return_feeder_options = _no_flix
        result = await feeder.feeder_return(
            "BER",
            "Flughafen BER - Terminal 1-2",
            "Berlin Hbf",
            "2030-09-22",
            datetime.fromisoformat("2030-09-22T09:00:00+02:00"),
            60,
            preference="dticket_first",
            deutschlandticket_available=True,
            split_ticket_check=True,
            include_flixbus=False,
            include_flixtrain=False,
        )
    finally:
        feeder._db_routes = original["_db_routes"]
        feeder._native_split_options = original["_native_split_options"]
        feeder._feeder_handoffs = original["_feeder_handoffs"]
        feeder._flix_return_feeder_options = original["_flix_return_feeder_options"]

    options = [result.get("selected_option"), *(result.get("alternatives") or [])]
    options = [item for item in options if isinstance(item, dict)]
    assert any(item.get("requires_deutschlandticket") is True for item in options), options
    assert any(item.get("requires_deutschlandticket") is not True and item.get("price_known") is True and float(item.get("total_price") or 0) > 0 for item in options), (
        "Bepreiste DB-Rückfahrt hinter unbepreisten Providerzeilen wurde verloren: " + repr(options)
    )


asyncio.run(_run_outbound())
asyncio.run(_run_return())
print("Bezahlte Alternativen trotz vorangestellter unbepreister DB-Zeilen: OK")
