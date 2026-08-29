from __future__ import annotations

import asyncio

import httpx

from reisevergleich import warnings


ROUTE = {
    "legs": [{
        "origin": {"name": "Start", "latitude": 51.0, "longitude": 10.0},
        "destination": {"name": "Ziel", "latitude": 51.4, "longitude": 10.4},
        "stopovers": [
            {"name": "Start", "latitude": 51.0, "longitude": 10.0},
            {"name": "Mitte", "latitude": 51.2, "longitude": 10.2},
            {"name": "Ziel", "latitude": 51.4, "longitude": 10.4},
        ],
    }],
}


def polygon(west: float, south: float, east: float, north: float) -> dict:
    return {"type": "FeatureCollection", "features": [{"type": "Feature", "geometry": {
        "type": "Polygon", "coordinates": [[[west, south], [east, south], [east, north], [west, north], [west, south]]],
    }}]}


def detail(identifier: str, *, title: str = "Gefahrstoffaustritt", severity: str = "Severe") -> dict:
    return {
        "identifier": identifier,
        "sender": "Leitstelle Testkreis",
        "info": [{
            "language": "de-DE", "headline": title, "severity": severity,
            "description": "<p>Fenster und Türen geschlossen halten.</p>",
            "senderName": "Leitstelle Testkreis",
            "area": [{"areaDesc": "Testkreis"}],
        }],
    }


async def run_provider_regressions() -> None:
    original = warnings._cached_json

    async def one_warning(namespace: str, path: str):
        if path.endswith("mapData.json"):
            return [{"id": "mow.test", "type": "Alert", "severity": "Severe", "i18nTitle": {"de": "Test"}}] if path.startswith("mowas/") else []
        if path.endswith(".geojson"):
            return polygon(10.1, 51.1, 10.3, 51.3)
        return detail("mow.test")

    warnings._cached_json = one_warning
    try:
        result = await warnings.warnings_for_routes([ROUTE])
        assert result["status"] == "ok"
        assert len(result["warnings"]) == 1
        item = result["warnings"][0]
        assert item["title"] == "Gefahrstoffaustritt"
        assert item["description"] == "Fenster und Türen geschlossen halten."
        assert item["location"] == "Testkreis"
        assert item["source"] == "NINA/BBK"
        assert item["affected_stops"] == ["Mitte"]

        async def no_warning(namespace: str, path: str):
            if path.endswith("mapData.json"):
                return [{"id": "mow.away", "type": "Alert"}] if path.startswith("mowas/") else []
            if path.endswith(".geojson"):
                return polygon(12.0, 53.0, 12.2, 53.2)
            raise AssertionError("Details dürfen ohne geografischen Treffer nicht geladen werden")

        warnings._cached_json = no_warning
        empty = await warnings.warnings_for_routes([ROUTE])
        assert empty == {"status": "empty", "warnings": [], "source": "NINA/BBK"}

        async def multiple(namespace: str, path: str):
            if path == "mowas/mapData.json":
                return [
                    {"id": "minor", "type": "Alert", "severity": "Minor"},
                    {"id": "extreme", "type": "Alert", "severity": "Extreme"},
                    {"id": "cancelled", "type": "Cancel", "severity": "Extreme"},
                ]
            if path.endswith("mapData.json"):
                return []
            if path.endswith(".geojson"):
                return polygon(9.9, 50.9, 10.5, 51.5)
            identifier = path.split("/")[-1].removesuffix(".json")
            return detail(identifier, title=identifier, severity=identifier.capitalize())

        warnings._cached_json = multiple
        many = await warnings.warnings_for_routes([ROUTE])
        assert [item["id"] for item in many["warnings"]] == ["extreme", "minor"]

        async def nationwide(namespace: str, path: str):
            if path == "mowas/mapData.json":
                return [{"id": "national", "type": "Alert"}]
            if path.endswith("mapData.json"):
                return []
            if path.endswith(".geojson"):
                return polygon(5.0, 47.0, 16.0, 56.0)
            raise AssertionError("Deutschlandweite Meldung darf nicht detailliert geladen werden")

        warnings._cached_json = nationwide
        broad = await warnings.warnings_for_routes([ROUTE])
        assert broad["warnings"] == []

        async def unavailable(namespace: str, path: str):
            raise httpx.ConnectError("offline")

        warnings._cached_json = unavailable
        failed = await warnings.warnings_for_routes([ROUTE])
        assert failed == {"status": "unavailable", "warnings": [], "source": "NINA/BBK"}
    finally:
        warnings._cached_json = original


async def cache_regression() -> None:
    original = warnings.cached_call
    captured = {}

    async def fake_cached_call(namespace, key, ttl, producer):
        captured.update(namespace=namespace, key=key, ttl=ttl)
        return []

    warnings.cached_call = fake_cached_call
    try:
        assert await warnings._cached_json("nina-map-v1", "mowas/mapData.json") == []
        assert captured["namespace"] == "nina-map-v1"
        assert captured["ttl"] >= 60
    finally:
        warnings.cached_call = original


async def airport_coordinate_regression() -> None:
    original_resolver = warnings._airport_points
    original_cache = warnings._cached_json
    calls = []

    async def resolve_airports(route):
        calls.append(route)
        return [
            {"name": "Flughafen FRA Terminal 1", "latitude": 50.0333, "longitude": 8.5706},
            {"name": "Flughafen BER", "latitude": 52.3667, "longitude": 13.5033},
        ]

    async def airport_warning(namespace: str, path: str):
        if path == "mowas/mapData.json":
            return [{"id": "airport", "type": "Alert", "severity": "Moderate"}]
        if path.endswith("mapData.json"):
            return []
        if path.endswith(".geojson"):
            return polygon(8.54, 50.01, 8.61, 50.06)
        return detail("airport", title="Polizeieinsatz am Terminal 1", severity="Moderate")

    warnings._airport_points = resolve_airports
    warnings._cached_json = airport_warning
    try:
        result = await warnings.warnings_for_routes([{
            "warning_geocode": True,
            "origin": {"name": "Flughafen FRA"},
            "destination": {"name": "Flughafen BER"},
        }])
        assert calls
        assert result["status"] == "ok"
        assert result["warnings"][0]["title"] == "Polizeieinsatz am Terminal 1"
        assert result["warnings"][0]["affected_stops"] == ["Flughafen FRA Terminal 1"]
        assert "transport" not in result["warnings"][0]
    finally:
        warnings._airport_points = original_resolver
        warnings._cached_json = original_cache


asyncio.run(run_provider_regressions())
asyncio.run(cache_regression())
asyncio.run(airport_coordinate_regression())
print("NINA/BBK Provider, Geofilter, Leer-/Mehrfachfälle und Cache: OK")
