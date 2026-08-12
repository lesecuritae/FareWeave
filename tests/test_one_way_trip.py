import asyncio

from reisevergleich import compare
from reisevergleich.models import TripRequest


request = TripRequest(
    travel_mode="ground",
    journey_type="one_way",
    origin="Alpha",
    destination="Beta",
    departure_date="2030-08-19",
    duration_value=0,
    include_hotel=False,
)
assert request.stay_nights == 0


route = {
    "id": "outbound",
    "departure": "2030-08-19T06:00+02:00",
    "arrival": "2030-08-19T09:00+02:00",
    "duration_minutes": 180,
    "transfers": 1,
    "price": 29.90,
    "currency": "EUR",
    "legs": [{"line": "RE 1"}, {"line": "ICE 2"}],
}


async def fake_compare_trip(_request):
    return {
        "status": "ok",
        "search_mode": "price_compare",
        "query": _request.model_dump(),
        "db_options": [route],
        "flix_options": [],
        "recommendation": {"cheapest_with_live_price": route, "fastest": route},
        "split_ticket": {"status": "skipped"},
        "warnings": [],
    }


async def run():
    original = compare.compare_trip
    compare.compare_trip = fake_compare_trip
    try:
        result = await compare.compare_ground_round_trip(
            origin="Alpha",
            destination="Beta",
            outbound_date="2030-08-19",
            return_date=None,
            stay_nights=0,
            departure_after="06:00",
            preference="cheapest",
            include_flixtrain=True,
            include_flixbus=True,
            max_transfers=None,
            max_results=3,
            split_ticket_check=True,
            deutschlandticket_mode="exclude",
            one_way=True,
        )
    finally:
        compare.compare_trip = original

    assert result["status"] == "ok"
    assert result["route"]["stay_nights"] == 0
    assert result["route"]["return_date"] is None
    assert result["return"] is None
    assert result["trip_chain"] == ["outbound_ground"]
    assert result["outbound"]["db_options"][0]["id"] == "outbound"


asyncio.run(run())
print("Einweg-Reise mit null Nächten: OK")
