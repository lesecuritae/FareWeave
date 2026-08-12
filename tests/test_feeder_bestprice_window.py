from __future__ import annotations

import asyncio
from datetime import datetime

import reisevergleich.feeder as feeder


async def check_hard_window_uses_timetable_search() -> None:
    calls: list[dict] = []

    async def fake_db_routes(origin, destination, travel_date, departure_after, **kwargs):
        calls.append({
            "origin": origin,
            "destination": destination,
            "travel_date": travel_date,
            "departure_after": departure_after,
            **kwargs,
        })
        return [], [], "dbnav"

    async def no_split(*args, **kwargs):
        return []

    async def no_flix(*args, **kwargs):
        return [], {"tested": True}

    originals = (
        feeder._db_routes,
        feeder._native_split_options,
        feeder._feeder_handoffs,
        feeder._flix_outbound_feeder_options,
    )
    try:
        feeder._db_routes = fake_db_routes
        feeder._native_split_options = no_split
        feeder._feeder_handoffs = lambda *args, **kwargs: []
        feeder._flix_outbound_feeder_options = no_flix
        await feeder.feeder_outbound(
            "Berlin Hbf",
            "BER",
            "Flughafen BER - Terminal 1-2",
            "2030-09-15",
            "06:00",
            datetime.fromisoformat("2030-09-15T13:45:00+02:00"),
            120,
            deutschlandticket_available=False,
            split_ticket_check=False,
            include_flixbus=False,
            include_flixtrain=False,
        )
    finally:
        (
            feeder._db_routes,
            feeder._native_split_options,
            feeder._feeder_handoffs,
            feeder._flix_outbound_feeder_options,
        ) = originals

    paid = [call for call in calls if call.get("mode") == "all"]
    assert paid, calls
    assert all(call.get("bestprice") is not True for call in paid), (
        "Bestpreissuche ist eine Tagespreissuche und darf die harte "
        "departure_after-Fahrplansuche des Flughafenzubringers nicht ersetzen: "
        + repr(paid)
    )


asyncio.run(check_hard_window_uses_timetable_search())
print("Harter Zubringer-Zeitrahmen verwendet keine Tages-Bestpreissuche: OK")
