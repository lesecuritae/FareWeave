from __future__ import annotations

import asyncio
from datetime import date

from reisevergleich import service
from reisevergleich.models import PriceCalendarRequest, StationSelection


def request(days: int) -> PriceCalendarRequest:
    return PriceCalendarRequest(
        travel_mode="ground", journey_type="one_way",
        origin="Leipzig Hbf", destination="Frankfurt(Main) Hbf",
        departure_date="2030-10-27", departure_after="03:00", calendar_days=days,
        include_hotel=False,
        origin_station=StationSelection(name="Leipzig Hbf", provider="db", provider_id="8010205"),
        destination_station=StationSelection(name="Frankfurt(Main) Hbf", provider="db", provider_id="8000105"),
    )


async def exercise(days: int) -> dict:
    active = 0
    maximum = 0

    async def fake_search(day_request):
        nonlocal active, maximum
        active += 1
        maximum = max(maximum, active)
        await asyncio.sleep(0.001)
        active -= 1
        day = date.fromisoformat(day_request.departure_date).day
        connection = {"price": float(day), "currency":"EUR"} if day != 29 else {}
        return {
            "status":"ok", "search_mode":"ground_trip", "cache":{"journey_hit":day == 28},
            "response_context":{"outbound":{"connections":[connection]}},
        }

    original = service.search
    service.search = fake_search
    try:
        result = await service.price_calendar(request(days))
    finally:
        service.search = original
    assert maximum <= 2
    return result


for count in (3, 7, 14):
    result = asyncio.run(exercise(count))
    assert len(result["days"]) == count
    assert result["days"][0]["date"] == "2030-10-27"
    assert result["days"][0]["price"] == 27.0
    assert result["days"][1]["price"] == 28.0 and result["days"][1]["cache_hit"] is True
    assert result["days"][2]["price"] is None and result["days"][2]["price_available"] is False
    assert sum(day["cheapest"] for day in result["days"]) == 1

try:
    request(15)
except ValueError:
    pass
else:
    raise AssertionError("Mehr als 14 Kalendertage hätten abgelehnt werden müssen")

print("Flexible Preissuche 3/7/14 Tage, Tageszuordnung, Cache und Obergrenze: OK")

round_trip = service._calendar_day({
    "response_context": {
        "route":{"return_date":"2030-11-03"},
        "outbound":{"connections":[{"price":20.0,"currency":"EUR"}]},
        "return":{"connections":[{"price":50.0,"currency":"EUR"}]},
        "price_summary":{"round_trip_live_price":70.0,"currency":"EUR","complete":True},
    }
}, "2030-10-27")
assert round_trip["price"] == 70.0, "Kalenderpreis muss bei Hin- und Rückfahrt die vollständige Reise abbilden"
