from __future__ import annotations

import asyncio

from reisevergleich import trvl
from reisevergleich.compare import select_visible_ground_options
from reisevergleich.models import ReiseRequest

DATE = "2030-08-19"


def route(kind: str, hour: int, price: float, *, name: str | None = None) -> dict:
    modes = [kind] if kind != "mixed" else ["bus", "train"]
    return {
        "id": name or f"{kind}-{hour}-{price}",
        "provider": "DB" if kind == "db" else "flixbus",
        "db_source": "db" if kind == "db" else None,
        "type": "train" if kind == "db" else kind,
        "flix_kind": None if kind == "db" else kind,
        "departure": {"city": "Leipzig", "time": f"{DATE}T{hour:02d}:00:00+02:00"},
        "arrival": {"city": "Dortmund", "time": f"{DATE}T{hour + 2:02d}:00:00+02:00"},
        "duration_minutes": 120,
        "transfers": 0,
        "price": price,
        "currency": "EUR",
        "legs": [{"type": mode} for mode in modes],
    }


def request(max_results: int, **kwargs) -> ReiseRequest:
    return ReiseRequest(
        origin="Leipzig Hbf",
        destination="Dortmund Hbf",
        travel_date=DATE,
        departure_after=kwargs.pop("departure_after", "06:00"),
        max_results=max_results,
        split_ticket_check=False,
        **kwargs,
    )


def composition(routes: list[dict]) -> tuple[int, int, int, int]:
    return (
        sum(item.get("db_source") == "db" for item in routes),
        sum(item.get("flix_kind") == "train" for item in routes),
        sum(item.get("flix_kind") == "bus" for item in routes),
        sum(item.get("flix_kind") == "mixed" for item in routes),
    )


def test_flix_city_query() -> None:
    assert trvl._flix_city_query("Leipzig Hbf") == "Leipzig"
    assert trvl._flix_city_query("Görlitz Hauptbahnhof") == "Görlitz"
    assert trvl._flix_city_query("Frankfurt(Main) Hbf") == "Frankfurt"
    assert trvl._flix_city_query("Dortmund Central Station (FlixTrain)") == "Dortmund"
    assert trvl._flix_city_query("Görlitz (bus station)") == "Görlitz"
    assert trvl._flix_city_query("Leipzig Messe") == "Leipzig Messe"
    assert trvl._flix_transfer_requirement(
        {"station": "Görlitz", "station_id": "goerlitz-flix"},
        "Görlitz Hbf", "flix_stop_to_destination", {"goerlitz-flix"},
    ) is None


async def test_flix_pool_and_classification() -> None:
    raw = [
        route("bus", 7, 9.99),
        route("bus", 8, 10.99),
        route("bus", 9, 12.99),
        route("bus", 10, 15.99),
        route("train", 11, 19.99),
        route("mixed", 12, 17.99),
        route("train", 13, 21.99),
        route("train", 5, 1.99, name="outside-window"),
        route("bus", 7, 9.99),  # duplicate
    ]
    raw[0]["departure"]["station"] = "Leipzig Messe"
    raw[-1]["departure"]["station"] = "Leipzig Messe"
    original = trvl.run_json_command
    trvl.run_json_command = lambda command, timeout: {
        "ok": True,
        "data": {"routes": raw},
        "raw": {"code": 0, "command": command},
    }
    try:
        result = await trvl.flix_search(request(3, preference="cheapest"))
        assert result["raw_route_count"] == 9
        assert result["candidate_counts"] == {"train": 2, "bus": 4, "mixed": 1}, result
        assert len(result["candidate_routes"]) == 7
        assert composition(result["routes"])[1:] == (2, 1, 0), result
        assert result["routes"][0]["provider"] == "FlixTrain"
        assert result["routes"][1]["provider"] == "FlixBus"
        same_city_bus = next(item for item in result["candidate_routes"] if item.get("departure_access"))
        assert same_city_bus["departure"]["station"] == "Leipzig Messe"
        assert same_city_bus["direct_from_requested_origin"] is False
        assert same_city_bus["departure_access"]["status"] == "connection_required"
        assert same_city_bus["departure_access"]["additional_cost"] is None
        assert same_city_bus["price_complete"] is False
        assert same_city_bus["self_managed_transfers"] == 1
        assert all(item["departure"]["time"] >= f"{DATE}T06:00" for item in result["candidate_routes"])
        mixed = next(item for item in result["candidate_routes"] if item["flix_kind"] == "mixed")
        assert mixed["provider"] == "FlixBus/FlixTrain"

        one = await trvl.flix_search(request(1, preference="cheapest"))
        assert len(one["routes"]) == 1 and one["routes"][0]["flix_kind"] == "bus"

        disabled = await trvl.flix_search(request(8, include_flixbus=False, include_flixtrain=False))
        assert disabled["routes"] == [] and disabled["candidate_routes"] == []
    finally:
        trvl.run_json_command = original


def test_total_budget() -> None:
    db = [route("db", 6 + index, 30 + index) for index in range(10)]
    train = [route("train", 16, 19.99), route("train", 17, 21.99)]
    bus = [route("bus", 18, 9.99), route("bus", 19, 12.99)]
    extra_flix = [route("bus", 20, 15.99), route("mixed", 21, 8.99)]

    assert composition(select_visible_ground_options(db, train + bus, request(10))) == (6, 2, 2, 0)
    assert composition(select_visible_ground_options(db, train[:1] + bus, request(10))) == (7, 1, 2, 0)
    assert composition(select_visible_ground_options(db, train, request(10))) == (8, 2, 0, 0)
    assert composition(select_visible_ground_options(db, bus, request(10))) == (8, 0, 2, 0)
    assert composition(select_visible_ground_options(db, train[:1] + bus[:1], request(10))) == (8, 1, 1, 0)
    assert composition(select_visible_ground_options(db, [], request(10))) == (10, 0, 0, 0)
    assert composition(select_visible_ground_options(db[:4], train + bus + extra_flix, request(10))) == (4, 2, 3, 1)

    two = select_visible_ground_options(db, train + bus, request(2))
    assert composition(two) == (0, 1, 1, 0), two

    one = select_visible_ground_options(db, train + bus, request(1, preference="cheapest"))
    assert len(one) == 1 and one[0]["flix_kind"] == "bus"

    disabled_request = request(10, include_flixbus=False, include_flixtrain=False)
    assert composition(select_visible_ground_options(db, [], disabled_request)) == (10, 0, 0, 0)


asyncio.run(test_flix_pool_and_classification())
test_total_budget()
test_flix_city_query()
print("Flix-Rohpool und sichtbare DB-/Flix-Auswahl: OK")

# Generic station-to-station access/egress composition regressions.
from reisevergleich import flix_connections

assert flix_connections._plausible_detour(300, 270)
assert not flix_connections._plausible_detour(720, 60)


def flix_route(origin_stop: str, destination_stop: str = "Dortmund Hbf") -> dict:
    item = route("bus", 10, 9.99)
    item["provider"] = "FlixBus"
    item["flix_kind"] = "bus"
    item["departure"]["station"] = origin_stop
    item["arrival"]["station"] = destination_stop
    if origin_stop != "Berlin Hbf":
        item["departure_access"] = {
            "required": True, "status": "connection_required",
            "actual_flix_stop": origin_stop, "requested_station": "Berlin Hbf",
        }
    return item


def local_route(departure: str, arrival: str, price=None) -> dict:
    return {
        "provider": "DB", "db_source": "db", "departure": f"{DATE}T{departure}:00+02:00",
        "arrival": f"{DATE}T{arrival}:00+02:00", "duration_minutes": 10,
        "transfers": 0, "price": price, "currency": "EUR", "legs": [{"mode": "regional"}],
    }


async def test_generic_access_egress() -> None:
    original_db = flix_connections.db_search_with_retry
    original_transit = flix_connections.transitous_search
    supplied = [local_route("09:05", "09:20", 3.20)]

    async def fake_db(**kwargs):
        return ({"journeys": list(supplied)}, [])

    async def fake_transit(*args, **kwargs):
        return {"routes": []}

    flix_connections.db_search_with_retry = fake_db
    flix_connections.transitous_search = fake_transit
    try:
        base_request = ReiseRequest(
            origin="Berlin Hbf", destination="Dortmund Hbf", travel_date=DATE,
            departure_after="09:00", max_results=10, split_ticket_check=False,
        )
        for stop in ("Berlin Südkreuz", "Berlin ZOB"):
            completed = await flix_connections.complete_flix_route(flix_route(stop), base_request)
            assert completed and completed["access_leg"]["kind"] == "access"
            assert completed["segments"][1]["departure"]["station"] == stop
            assert completed["departure"].startswith(f"{DATE}T09:05")
            assert completed["price"] == 13.19

        direct = flix_route("Berlin Hbf")
        direct.pop("departure_access", None)
        assert await flix_connections.complete_flix_route(direct, base_request) is direct

        egress = flix_route("Berlin Hbf", "Dortmund ZOB")
        egress.pop("departure_access", None)
        egress["arrival_egress"] = {
            "required": True, "status": "connection_required",
            "actual_flix_stop": "Dortmund ZOB", "requested_station": "Dortmund Hbf",
        }
        supplied[:] = [local_route("12:35", "12:50", 2.50)]
        completed = await flix_connections.complete_flix_route(egress, base_request)
        assert completed and completed["egress_leg"]["kind"] == "egress"
        assert completed["arrival"].startswith(f"{DATE}T12:50")

        supplied[:] = [local_route("08:55", "09:10", 3.20)]
        assert await flix_connections.complete_flix_route(flix_route("Berlin Südkreuz"), base_request) is None

        supplied[:] = [local_route("09:20", "09:50", 3.20)]
        assert await flix_connections.complete_flix_route(flix_route("Berlin Südkreuz"), base_request) is None

        supplied[:] = [local_route("09:05", "09:20", None)]
        dticket_request = base_request.model_copy(update={"deutschlandticket": True})
        completed = await flix_connections.complete_flix_route(flix_route("Berlin Südkreuz"), dticket_request)
        assert completed and completed["access_leg"]["price"] == 0.0
        assert completed["price"] == 9.99 and completed["duration_minutes"] == 175

        completed = await flix_connections.complete_flix_route(flix_route("Berlin Südkreuz"), base_request)
        assert completed and completed["price"] is None and completed["price_complete"] is False

        unresolved = flix_route("station-id")
        unresolved["departure_access"]["status"] = "unresolved_stop"
        assert await flix_connections.complete_flix_route(unresolved, base_request) is None

        cross_city_request = base_request.model_copy(update={"origin": "Leipzig Hbf", "departure_after": "08:00"})
        cross_city = flix_route("Berlin Südkreuz")
        cross_city["departure_access"]["requested_station"] = "Leipzig Hbf"
        supplied[:] = [local_route("08:05", "09:20", 19.90)]
        completed = await flix_connections.complete_flix_route(cross_city, cross_city_request)
        assert completed and completed["departure"].startswith(f"{DATE}T08:05")
        assert completed["segments"][1]["departure"]["station"] == "Berlin Südkreuz"

        munich_request = base_request.model_copy(update={"origin": "München Hbf"})
        munich = flix_route("München ZOB")
        munich["departure_access"]["requested_station"] = "München Hbf"
        supplied[:] = [local_route("09:05", "09:20", 3.20)]
        assert await flix_connections.complete_flix_route(munich, munich_request)
    finally:
        flix_connections.db_search_with_retry = original_db
        flix_connections.transitous_search = original_transit


asyncio.run(test_generic_access_egress())
print("Generische Flix-Access-/Egress-Verbindungen: OK")

async def test_dynamic_and_hard_manual_stop_selection() -> None:
    raw = [route("bus", 7, 9.99), route("bus", 8, 10.99)]
    raw[0]["departure"].update({"city": "Alpha", "station": "Alpha Nord", "station_id": "alpha-nord", "latitude": 1.0, "longitude": 2.0})
    raw[1]["departure"].update({"city": "Alpha", "station": "Alpha ZOB", "station_id": "alpha-zob", "latitude": 3.0, "longitude": 4.0})
    raw[0]["arrival"].update({"station": "Dortmund Hbf", "station_id": "dortmund-hbf"})
    raw[1]["arrival"].update({"station": "Dortmund Hbf", "station_id": "dortmund-hbf"})
    original = trvl.run_json_command
    trvl.run_json_command = lambda command, timeout: {
        "ok": True, "data": {"routes": raw}, "raw": {"code": 0, "command": command},
    }
    try:
        probe_request = ReiseRequest(
            origin="Alpha Hbf", destination="Dortmund Hbf", travel_date=DATE,
            departure_after="06:00", max_results=10, split_ticket_check=False,
        )
        stops = await trvl.discover_flix_stops(probe_request)
        assert [(item["station_id"], item["name"]) for item in stops["origin_stops"]] == [
            ("alpha-nord", "Alpha Nord"), ("alpha-zob", "Alpha ZOB"),
        ]
        manual = await trvl.flix_search(probe_request.model_copy(update={"flix_origin_stop_id": "alpha-zob"}))
        assert len(manual["candidate_routes"]) == 1
        assert manual["candidate_routes"][0]["departure"]["station_id"] == "alpha-zob"
    finally:
        trvl.run_json_command = original


asyncio.run(test_dynamic_and_hard_manual_stop_selection())
print("Dynamische und harte manuelle Flix-Haltestellenwahl: OK")
