from __future__ import annotations

import asyncio

from reisevergleich import station_catalog
from reisevergleich.models import StationSelection, TripRequest


def test_station_selection_must_match_visible_name():
    try:
        TripRequest(
            travel_mode="ground", journey_type="one_way", origin="Frankfurt Hbf",
            destination="Leipzig Hbf", departure_date="2030-10-27",
            origin_station=StationSelection(name="Frankfurt Airport", provider="transitous", provider_id="airport"),
        )
    except ValueError:
        return
    raise AssertionError("Eine abweichende sichtbare Station hätte abgelehnt werden müssen")


def test_catalog_keeps_ambiguous_places_for_explicit_user_choice(monkeypatch):
    async def db(_query): return []
    async def flix(_query): return []
    async def transitous(_query):
        return [
            {"provider":"transitous", "provider_id":"at", "name":"Vienna Central Station", "region":"Wien", "country":"AT"},
            {"provider":"transitous", "provider_id":"us", "name":"Vienna", "region":"Virginia", "country":"US"},
        ]
    monkeypatch.setattr(station_catalog, "_db_locations", db)
    monkeypatch.setattr(station_catalog, "_flix_locations", flix)
    monkeypatch.setattr(station_catalog, "_transitous_locations", transitous)
    async def direct_cache(_namespace, _key, _ttl, loader): return await loader()
    monkeypatch.setattr(station_catalog, "cached_call", direct_cache)
    result = asyncio.run(station_catalog.search_stations("Vienna"))
    assert {item["provider_id"] for item in result["stations"]} == {"at", "us"}
    assert any("Virginia" in item["label"] for item in result["stations"])
    assert any("Wien" in item["label"] for item in result["stations"])
    assert result["requires_selection"] is True
    assert result["auto_selection"] is None


def test_catalog_automatically_uses_an_exact_station_among_multiple_hits(monkeypatch):
    async def db(_query):
        return [
            {"provider":"db", "provider_id":"8010205", "name":"Leipzig Hbf", "latitude":51.345, "longitude":12.382},
            {"provider":"db", "provider_id":"airport", "name":"Leipzig/Halle Flughafen", "latitude":51.423, "longitude":12.236},
        ]
    async def transitous(_query):
        return [{"provider":"transitous", "provider_id":"de:hbf", "name":"Leipzig Hbf", "latitude":51.345, "longitude":12.382}]
    async def flix(_query): return []
    monkeypatch.setattr(station_catalog, "_db_locations", db)
    monkeypatch.setattr(station_catalog, "_flix_locations", flix)
    monkeypatch.setattr(station_catalog, "_transitous_locations", transitous)
    async def direct_cache(_namespace, _key, _ttl, loader): return await loader()
    monkeypatch.setattr(station_catalog, "cached_call", direct_cache)
    result = asyncio.run(station_catalog.search_stations("Leipzig Hbf"))
    assert result["requires_selection"] is False
    assert result["auto_selection"]["name"] == "Leipzig Hbf"
    assert result["auto_selection"]["provider_ids"] == {"db":"8010205", "transitous":"de:hbf"}
    assert result["auto_selection"]["provider_alias_ids"] == {"db":["8010205"], "transitous":["de:hbf"]}


def test_catalog_requires_choice_even_for_one_city_result(monkeypatch):
    async def db(_query):
        return [{"provider":"db", "provider_id":"8000261", "name":"München Hbf", "latitude":48.14, "longitude":11.56}]
    async def transitous(_query):
        return [{"provider":"transitous", "provider_id":"de:munich", "name":"München Hbf", "latitude":48.14, "longitude":11.56}]
    async def flix(_query): return []
    monkeypatch.setattr(station_catalog, "_db_locations", db)
    monkeypatch.setattr(station_catalog, "_flix_locations", flix)
    monkeypatch.setattr(station_catalog, "_transitous_locations", transitous)
    async def direct_cache(_namespace, _key, _ttl, loader): return await loader()
    monkeypatch.setattr(station_catalog, "cached_call", direct_cache)
    result = asyncio.run(station_catalog.search_stations("Munich"))
    assert len(result["stations"]) == 1
    assert result["requires_selection"] is True
    assert result["auto_selection"] is None


def test_main_stations_rank_before_exits_and_child_stops(monkeypatch):
    async def db(_query):
        return [
            {"provider":"db", "provider_id":"exit", "name":"Görlitz Hbf Südausgang", "latitude":51.146, "longitude":14.979},
            {"provider":"db", "provider_id":"main", "name":"Görlitz Hbf", "latitude":51.147, "longitude":14.980, "is_station":True},
        ]
    async def transitous(_query):
        return [{"provider":"transitous", "provider_id":"child", "name":"Görlitz Hbf Eingang", "parent_station":"main"}]
    async def flix(_query): return []
    monkeypatch.setattr(station_catalog, "_db_locations", db)
    monkeypatch.setattr(station_catalog, "_flix_locations", flix)
    monkeypatch.setattr(station_catalog, "_transitous_locations", transitous)
    async def direct_cache(_namespace, _key, _ttl, loader): return await loader()
    monkeypatch.setattr(station_catalog, "cached_call", direct_cache)
    exact = asyncio.run(station_catalog.search_stations("Görlitz Hbf"))
    city = asyncio.run(station_catalog.search_stations("Görlitz"))
    assert exact["stations"][0]["name"] == "Görlitz Hbf"
    assert city["stations"][0]["name"] == "Görlitz Hbf"


def test_city_requires_choice_ranks_main_station_and_hides_airport(monkeypatch):
    async def db(_query):
        return [
            {"provider":"db", "provider_id":"city", "name":"München", "latitude":48.13, "longitude":11.57, "is_station":True},
            {"provider":"db", "provider_id":"hbf", "name":"München Hbf", "latitude":48.14, "longitude":11.56, "is_station":True},
            {"provider":"db", "provider_id":"ost", "name":"München Ost", "latitude":48.13, "longitude":11.60, "is_station":True},
            {"provider":"db", "provider_id":"airport", "name":"München Flughafen Terminal", "latitude":48.35, "longitude":11.78, "is_station":True},
        ]
    async def empty(_query): return []
    monkeypatch.setattr(station_catalog, "_db_locations", db)
    monkeypatch.setattr(station_catalog, "_transitous_locations", empty)
    monkeypatch.setattr(station_catalog, "_flix_locations", empty)
    async def direct_cache(_namespace, _key, _ttl, producer): return await producer()
    monkeypatch.setattr(station_catalog, "cached_call", direct_cache)
    result = asyncio.run(station_catalog.search_stations("München"))
    assert result["stations"][0]["name"] == "München Hbf"
    assert "München Ost" in {item["name"] for item in result["stations"]}
    assert all("Flughafen" not in item["name"] for item in result["stations"])
    assert result["requires_selection"] is True and result["auto_selection"] is None


def test_known_central_station_names_have_no_secondary_penalty():
    for name in ("Leipzig Hbf", "Berlin Hbf", "Frankfurt(Main) Hbf", "Kassel-Wilhelmshöhe"):
        assert station_catalog._station_role_score(name, {"is_station": True}) >= 100
    for name in ("Görlitz Hbf Südausgang", "Berlin Hbf Eingang", "Kassel-Wilhelmshöhe Bahnsteig 1"):
        assert station_catalog._station_role_score(name) < 0
    assert station_catalog._station_role_score("München Ost", {"modes":["LONG_DISTANCE"]}) > station_catalog._station_role_score("München Harras", {"modes":["SUBURBAN"]})


def test_catalog_keeps_multiple_flix_ids_for_one_station_complex(monkeypatch):
    async def db(_query):
        return [{"provider":"db", "provider_id":"db-main", "name":"Berlin Hbf", "latitude":52.525, "longitude":13.369, "is_station":True}]
    async def transitous(_query):
        return [{"provider":"transitous", "provider_id":"transit-main", "name":"Berlin Hauptbahnhof", "latitude":52.525, "longitude":13.369}]
    async def flix(_query):
        return [
            {"provider":"flix", "provider_id":"flix-train", "name":"Berlin central train station", "latitude":52.525, "longitude":13.369, "parent_station":"berlin"},
            {"provider":"flix", "provider_id":"flix-bus", "name":"Berlin central bus stop", "latitude":52.526, "longitude":13.370, "parent_station":"berlin"},
        ]
    monkeypatch.setattr(station_catalog, "_db_locations", db)
    monkeypatch.setattr(station_catalog, "_transitous_locations", transitous)
    monkeypatch.setattr(station_catalog, "_flix_locations", flix)
    async def direct_cache(_namespace, _key, _ttl, loader): return await loader()
    monkeypatch.setattr(station_catalog, "cached_call", direct_cache)
    result = asyncio.run(station_catalog.search_stations("Berlin Hbf"))
    selected = result["auto_selection"]
    assert selected["provider_ids"].keys() == {"db", "transitous", "flix"}
    assert set(selected["provider_alias_ids"]["flix"]) == {"flix-train", "flix-bus"}


def test_reference_main_stations_map_across_all_providers(monkeypatch):
    names = ("Leipzig Hbf", "Berlin Hbf", "Frankfurt(Main) Hbf", "Kassel-Wilhelmshöhe", "Görlitz Hbf")
    async def loader(provider, query):
        return [{"provider":provider, "provider_id":f"{provider}:{query}", "name":query, "latitude":51.0, "longitude":12.0, "is_station":provider == "db"}]
    monkeypatch.setattr(station_catalog, "_db_locations", lambda query: loader("db", query))
    monkeypatch.setattr(station_catalog, "_transitous_locations", lambda query: loader("transitous", query))
    monkeypatch.setattr(station_catalog, "_flix_locations", lambda query: loader("flix", query))
    async def direct_cache(_namespace, _key, _ttl, producer): return await producer()
    monkeypatch.setattr(station_catalog, "cached_call", direct_cache)
    for name in names:
        selected = asyncio.run(station_catalog.search_stations(name))["auto_selection"]
        assert set(selected["provider_ids"]) == {"db", "transitous", "flix"}
