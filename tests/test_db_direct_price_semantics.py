from __future__ import annotations

import asyncio
from datetime import datetime

import reisevergleich.feeder as feeder


def route(origin: str, destination: str, departure: str, arrival: str) -> dict:
    return {
        "id": "priced",
        "provider": "Deutsche Bahn",
        "type": "train",
        "origin": origin,
        "destination": destination,
        "departure": departure,
        "arrival": arrival,
        "duration_minutes": 30,
        "price": 30.0,
        "best_split_price": 20.0,
        "currency": "EUR",
        "legs": [{
            "mode": "train",
            "line": "FEX",
            "origin": {"name": origin},
            "destination": {"name": destination},
            "departure": departure,
            "arrival": arrival,
        }],
    }


async def no_split(routes):
    return []


async def no_flix(*args, **kwargs):
    return [], {"tested": True}


async def outbound():
    original=(feeder._db_routes, feeder._native_split_options, feeder._feeder_handoffs, feeder._flix_outbound_feeder_options)
    async def fake_db(origin, destination, travel_date, departure_after, *, mode, **kwargs):
        if mode == "deutschlandticket":
            return [], [], "dbnav"
        return [route("Berlin Hbf", "BER Berlin Brandenburg Airport", "2030-09-15T08:00:00+02:00", "2030-09-15T08:30:00+02:00")], [], "dbnav"
    try:
        feeder._db_routes=fake_db
        feeder._native_split_options=no_split
        feeder._feeder_handoffs=lambda *a, **k: []
        feeder._flix_outbound_feeder_options=no_flix
        result=await feeder.feeder_outbound(
            "Berlin Hbf","BER","Flughafen BER - Terminal 1-2","2030-09-15","06:00",
            datetime.fromisoformat("2030-09-15T13:45:00+02:00"),120,
            deutschlandticket_available=False,split_ticket_check=False,include_flixbus=False,include_flixtrain=False,
        )
    finally:
        feeder._db_routes, feeder._native_split_options, feeder._feeder_handoffs, feeder._flix_outbound_feeder_options=original
    selected=result.get("selected_option") or {}
    assert selected.get("type") == "db_direct", selected
    assert selected.get("total_price") == 30.0, f"db_direct darf nicht den best_split_price 20.0 als Direktpreis ausgeben: {selected}"


async def back():
    original=(feeder._db_routes, feeder._native_split_options, feeder._feeder_handoffs, feeder._flix_return_feeder_options)
    async def fake_db(origin, destination, travel_date, departure_after, *, mode, **kwargs):
        if mode == "deutschlandticket":
            return [], [], "dbnav"
        return [route("BER Berlin Brandenburg Airport", "Berlin Hbf", "2030-09-22T10:30:00+02:00", "2030-09-22T11:00:00+02:00")], [], "dbnav"
    try:
        feeder._db_routes=fake_db
        feeder._native_split_options=no_split
        feeder._feeder_handoffs=lambda *a, **k: []
        feeder._flix_return_feeder_options=no_flix
        result=await feeder.feeder_return(
            "BER","Flughafen BER - Terminal 1-2","Berlin Hbf","2030-09-22",
            datetime.fromisoformat("2030-09-22T09:00:00+02:00"),60,
            deutschlandticket_available=False,split_ticket_check=False,include_flixbus=False,include_flixtrain=False,
        )
    finally:
        feeder._db_routes, feeder._native_split_options, feeder._feeder_handoffs, feeder._flix_return_feeder_options=original
    selected=result.get("selected_option") or {}
    assert selected.get("type") == "db_direct", selected
    assert selected.get("total_price") == 30.0, f"db_direct-Rückfahrt darf nicht den best_split_price 20.0 als Direktpreis ausgeben: {selected}"


asyncio.run(outbound())
asyncio.run(back())
print("DB-Direktpreis bleibt Direktpreis; Splitpreis bleibt Split-Alternative: OK")
