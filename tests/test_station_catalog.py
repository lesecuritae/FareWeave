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


def test_catalog_automatically_uses_an_unambiguous_alias(monkeypatch):
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
    assert result["requires_selection"] is False
    assert result["auto_selection"]["provider_ids"] == {"db":"8000261", "transitous":"de:munich"}


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


def test_known_central_station_names_have_no_secondary_penalty():
    for name in ("Leipzig Hbf", "Berlin Hbf", "Frankfurt(Main) Hbf", "Kassel-Wilhelmshöhe"):
        assert station_catalog._station_role_score(name, {"is_station": True}) >= 100
    for name in ("Görlitz Hbf Südausgang", "Berlin Hbf Eingang", "Kassel-Wilhelmshöhe Bahnsteig 1"):
        assert station_catalog._station_role_score(name) < 0
