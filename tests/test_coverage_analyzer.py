import asyncio

from reisevergleich.coverage import analyzer, cache, mapper, provider
from reisevergleich.db import compact_route


def test_mapper_prefers_geometry_and_interpolates():
    route = {"geometry": {"coordinates": [[13.369, 52.525], [11.558, 48.14]]}}
    points = mapper.sample_route(mapper.route_waypoints(route))
    assert 100 <= len(points) <= mapper.MAX_ROUTE_POINTS
    assert points[-1]["distance_km"] > 450


def test_mapper_extracts_provider_neutral_stops():
    route = {"legs": [
        {"origin": {"name": "Berlin Hbf", "lat": 52.525, "lon": 13.369}, "destination": "Leipzig Hbf"},
        {"origin": "Leipzig Hbf", "destination": "München Hbf"},
    ]}
    assert [item["name"] for item in mapper.route_waypoints(route)] == ["Berlin Hbf", "Leipzig Hbf", "München Hbf"]


def test_db_stopover_coordinates_reach_mapper():
    route = compact_route({
        "id": "route-1",
        "origin": "Berlin Hbf",
        "destination": "München Hbf",
        "legs": [{
            "origin": {"name": "Berlin Hbf", "id": "berlin"},
            "destination": {"name": "München Hbf", "id": "munich"},
            "stopovers": [
                {"name": "Berlin Hbf", "id": "berlin", "latitude": 52.525, "longitude": 13.369},
                {"name": "München Hbf", "id": "munich", "latitude": 48.14, "longitude": 11.558},
            ],
        }],
    })
    points = mapper.route_waypoints(route)
    assert [(item["latitude"], item["longitude"]) for item in points] == [(52.525, 13.369), (48.14, 11.558)]


def test_coverage_cache_uses_versioned_route_key(monkeypatch):
    observed = {}

    async def fake_cached_call(namespace, params, ttl, producer):
        observed.update(namespace=namespace, params=params, ttl=ttl)
        return await producer()

    async def producer():
        return {"status": "ok"}

    monkeypatch.setattr(cache, "cached_call", fake_cached_call)
    result = asyncio.run(cache.get_or_analyze("known-route", producer))
    assert result == {"status": "ok"}
    assert observed == {
        "namespace": "coverage-v1.1.0",
        "params": {"route_id": "known-route"},
        "ttl": 7 * 24 * 60 * 60,
    }


def test_official_raster_is_local_and_operator_neutral():
    assert provider.network_count({"latitude": 52.525, "longitude": 13.369}) in {0, 1, 2, 3, 4}
    assert provider.network_count({"latitude": 48.8566, "longitude": 2.3522}) is None
    assert [threshold for _, threshold in provider.PROVIDERS.values()] == [1, 2, 3]


def test_analyzer_isolates_provider_failure(monkeypatch):
    async def resolved(_route):
        return [{"name": "A", "latitude": 52.5, "longitude": 13.4}, {"name": "B", "latitude": 52.6, "longitude": 13.5}]
    async def failed(_points):
        raise TimeoutError("source slow")
    async def direct(_key, producer):
        return await producer()
    monkeypatch.setattr(analyzer, "resolve_waypoints", resolved)
    monkeypatch.setattr(analyzer, "sample", failed)
    monkeypatch.setattr(analyzer, "get_or_analyze", direct)
    result = asyncio.run(analyzer.analyze_route({"origin": "A", "destination": "B"}))
    assert result["status"] == "unavailable"
    assert result["message"] == "Mobilfunkanalyse momentan nicht verfügbar"


def test_network_summary_and_tunnel_limit(monkeypatch):
    async def resolved(_route):
        return [{"name": "A", "latitude": 52.5, "longitude": 13.4}, {"name": "B", "latitude": 52.6, "longitude": 13.5}]
    async def samples(points):
        values = [True] + [False] * max(0, len(points) - 2) + [True]
        return {key: list(values) for key in provider.PROVIDERS}
    async def direct(_key, producer):
        return await producer()
    monkeypatch.setattr(analyzer, "resolve_waypoints", resolved)
    monkeypatch.setattr(analyzer, "sample", samples)
    monkeypatch.setattr(analyzer, "get_or_analyze", direct)
    result = asyncio.run(analyzer.analyze_route({"origin": "A", "destination": "B"}))
    assert result["status"] == "ok"
    assert {item["name"] for item in result["networks"]} == {"Mindestens 1 Netz", "Mindestens 2 Netze", "Mindestens 3 Netze"}
    assert result["tunnels"]["status"] == "not_available"
