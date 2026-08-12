import asyncio

from reisevergleich import ground_mixed
from reisevergleich import compare


def route(origin, destination, departure, arrival, *, line, price=None):
    value = {
        "origin": origin, "destination": destination,
        "departure": departure, "arrival": arrival,
        "duration_minutes": 30, "legs": [{
            "mode": "train", "line": line, "origin": origin, "destination": destination,
            "departure": departure, "arrival": arrival,
        }],
    }
    if price is not None:
        value.update({"price": price, "currency": "EUR"})
    return value


async def fake_db(origin, destination, travel_date, departure_after, *, mode, **kwargs):
    if (origin, destination, mode) == ("Alpha Süd", "Alpha Hbf", "deutschlandticket"):
        return [route(origin, destination, "2030-11-24T06:10+01:00", "2030-11-24T06:32+01:00", line="S1")], [], "dbnav"
    if (origin, destination, mode) == ("Beta Hbf", "Gamma Hbf", "deutschlandticket"):
        return [route(origin, destination, "2030-11-24T11:21+01:00", "2030-11-24T11:37+01:00", line="RE11")], [], "dbnav"
    return [], [], "dbnav"


async def fake_flix(origin, targets, travel_date, departure_after, **kwargs):
    if origin == "Alpha Hbf" and "Beta Hbf" in targets:
        return [{
            "provider": "FlixTrain", "flix_kind": "train", "type": "train",
            "departure": {"city": "Delta", "time": "2030-11-24T06:55+01:00"},
            "arrival": {"station": "Beta Hbf", "time": "2030-11-24T11:00+01:00"},
            "duration_minutes": 245, "price": 18.99, "currency": "EUR", "legs": [],
        }, {
            "provider": "FlixTrain", "flix_kind": "train", "type": "train",
            "departure": {"station": "Alpha Hbf", "time": "2030-11-24T06:55+01:00"},
            "arrival": {"station": "Beta Hbf", "time": "2030-11-24T11:00+01:00"},
            "duration_minutes": 245, "price": 19.99, "currency": "EUR", "legs": [],
        }], True
    return [], True


async def run():
    old_db = ground_mixed._db_routes
    old_flix = ground_mixed._flix_routes_for_targets
    try:
        ground_mixed._db_routes = fake_db
        ground_mixed._flix_routes_for_targets = fake_flix
        options = await ground_mixed._flix_three_part(
            "Alpha Süd", "Gamma Hbf", "2030-11-24", "06:00",
            ["Alpha Hbf", "Beta Hbf"], 15,
            include_flixbus=True, include_flixtrain=True,
        )
    finally:
        ground_mixed._db_routes = old_db
        ground_mixed._flix_routes_for_targets = old_flix

    options = ground_mixed._dedupe(options + options)
    assert len(options) == 1, options
    option = options[0]
    assert option["type"] == "deutschlandticket_plus_flix_plus_deutschlandticket"
    assert option["total_price"] == 19.99
    assert option["split_stations"] == ["Alpha Hbf", "Beta Hbf"]
    assert [segment.get("ticket") for segment in option["segments"]] == ["Deutschlandticket", None, "Deutschlandticket"]
    assert option["segments"][1]["provider"] == "FlixTrain"
    assert option["departure"] == "2030-11-24T06:10:00+01:00"
    assert option["arrival"] == "2030-11-24T11:37:00+01:00"



async def run_dticket_only():
    original = compare.deutschlandticket
    async def fake_dticket(request):
        return {"status": "ok", "routes": [route(request.origin, request.destination, f"{request.travel_date}T06:10+01:00", f"{request.travel_date}T07:10+01:00", line="RE")], "warning": "Tarifprüfung"}
    try:
        compare.deutschlandticket = fake_dticket
        result = await compare.compare_ground_round_trip(
            origin="Startstadt", destination="Zielstadt", outbound_date="2030-11-24",
            return_date="2030-11-26", stay_nights=None, departure_after="06:00",
            preference="fastest", include_flixtrain=True, include_flixbus=True,
            max_transfers=None, max_results=3, split_ticket_check=True,
            deutschlandticket_mode="only", split_candidates=["Umsteigebahnhof"],
        )
    finally:
        compare.deutschlandticket = original
    assert result["status"] == "ok", result
    assert result["deutschlandticket"]["only"] is True
    assert result["outbound"]["db_options"] == []
    assert result["outbound"]["flix_options"] == []
    assert result["outbound"]["mixed_ticket_options"] == []
    assert result["price_summary"]["round_trip_live_price"] == 0.0
    assert result["price_summary"]["price_semantics"] == "deutschlandticket_covered_additional_cost"


asyncio.run(run())
asyncio.run(run_dticket_only())
print("Ground-Mischkette D-Ticket + Flix + D-Ticket: OK")
