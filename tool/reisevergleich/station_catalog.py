from __future__ import annotations

import asyncio
from math import asin, cos, radians, sin, sqrt
from typing import Any

import httpx

from .cache import cached_call
from .config import APP_VERSION, DB_API_URL, TRANSITOUS_TIMEOUT, TRANSITOUS_URL, TRANSITOUS_USER_AGENT
from .gtfs_flix import discover_stops
from .location_resolver import exact_location_key, has_airport_context, location_candidates, location_key

_CACHE_TTL = 300
_RANKING_GENERATION = "stations-v8"


def _base_station_query(value: str) -> str:
    return " ".join(word for word in value.split() if exact_location_key(word) not in {"hbf", "hauptbahnhof", "bahnhof", "station"})


def _distance_km(left: dict[str, Any], right: dict[str, Any]) -> float | None:
    try:
        lat1, lon1 = radians(float(left["latitude"])), radians(float(left["longitude"]))
        lat2, lon2 = radians(float(right["latitude"])), radians(float(right["longitude"]))
    except (KeyError, TypeError, ValueError):
        return None
    dlat, dlon = lat2 - lat1, lon2 - lon1
    value = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    return 6371 * 2 * asin(sqrt(value))


_SECONDARY_STATION_WORDS = {
    "ausgang", "südausgang", "nordausgang", "ostausgang", "westausgang",
    "eingang", "zugang", "bahnsteig", "gleis", "vorplatz", "parkplatz", "park",
}


def _station_role_score(name: str, item: dict[str, Any] | None = None) -> int:
    words = set(exact_location_key(name).replace("-", " ").split())
    score = 400 if words & {"hbf", "hauptbahnhof", "central", "centrale", "centraal"} else 0
    if words & _SECONDARY_STATION_WORDS:
        score -= 350
    item = item or {}
    modes = {str(mode).upper() for mode in item.get("modes") or []}
    if modes & {"HIGHSPEED_RAIL", "LONG_DISTANCE", "NIGHT_RAIL"}:
        score += 260
    elif "REGIONAL_RAIL" in modes:
        score += 90
    if "COACH" in modes:
        score += 120
    if item.get("parent_station"):
        score -= 220
    if str(item.get("location_type") or "") == "1" or item.get("is_station") is True:
        score += 100
    return score


def _score(query: str, name: str, provider: str, item: dict[str, Any] | None = None) -> int:
    exact_query, exact_name = exact_location_key(query), exact_location_key(name)
    alias_query, alias_name = location_key(query), location_key(name)
    score = {"db": 30, "transitous": 20, "flix": 10}.get(provider, 0)
    if exact_query == exact_name:
        city_only_penalty = 450 if len(exact_query.split()) == 1 else 0
        return score + 1000 - city_only_penalty + _station_role_score(name, item)
    if exact_location_key(_base_station_query(query)) == exact_name:
        return score + 850 + _station_role_score(name, item)
    if exact_name.startswith(exact_query + " "):
        score += 600
    elif alias_query == alias_name:
        score += 500
    elif alias_name.startswith(alias_query + " "):
        score += 350
    elif set(alias_query.split()) <= set(alias_name.split()):
        score += 200
    return score + _station_role_score(name, item)


async def _db_locations(query: str) -> list[dict[str, Any]]:
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.get(f"{DB_API_URL}/locations", params={"q": query})
        response.raise_for_status()
    return response.json().get("locations") or []


async def _transitous_locations(query: str) -> list[dict[str, Any]]:
    async with httpx.AsyncClient(
        timeout=TRANSITOUS_TIMEOUT,
        headers={"User-Agent": TRANSITOUS_USER_AGENT, "Accept": "application/json"},
    ) as client:
        response = await client.get(
            f"{TRANSITOUS_URL}/api/v1/geocode",
            params={"text": query, "type": "STOP", "language": "de", "numResults": 20},
        )
        response.raise_for_status()
    items = response.json()
    return [{
        "provider": "transitous",
        "provider_id": str(item["id"]),
        "name": str(item.get("name") or item["id"]),
        "latitude": item.get("lat", item.get("latitude")),
        "longitude": item.get("lon", item.get("longitude")),
        "country": item.get("country"),
        "region": next((area.get("name") for area in item.get("areas") or [] if area.get("unique")), None),
        "modes": item.get("modes") or [],
        "parent_station": item.get("parentStation") or item.get("parent_station"),
        "location_type": item.get("locationType") or item.get("location_type"),
    } for item in items if isinstance(item, dict) and item.get("id")]


async def _flix_locations(query: str) -> list[dict[str, Any]]:
    result = await discover_stops(query, query)
    return [{
        "provider": "flix", "provider_id": item["station_id"], "name": item["name"],
        "latitude": item.get("latitude"), "longitude": item.get("longitude"),
        "parent_station": item.get("parent_station"), "location_type": item.get("location_type"),
    } for item in result.get("origin_stops") or []]


async def _all_queries(loader, queries: tuple[str, ...]) -> list[dict[str, Any]]:
    results = await asyncio.gather(*(loader(query) for query in queries), return_exceptions=True)
    output: list[dict[str, Any]] = []
    for result in results:
        if not isinstance(result, BaseException): output.extend(result)
    return output


async def _search_uncached(normalized: str, limit: int) -> dict[str, Any]:
    queries = list(location_candidates(normalized)[:2])
    base_query = _base_station_query(normalized)
    if base_query and exact_location_key(base_query) not in {exact_location_key(query) for query in queries}:
        queries.append(base_query)
    results = await asyncio.gather(
        _all_queries(_db_locations, queries),
        _all_queries(_transitous_locations, queries),
        _all_queries(_flix_locations, queries),
        return_exceptions=True,
    )
    candidates: list[dict[str, Any]] = []
    statuses: dict[str, str] = {}
    for provider, result in zip(("db", "transitous", "flix"), results):
        if isinstance(result, BaseException):
            statuses[provider] = "failed"
            continue
        statuses[provider] = "ok"
        candidates.extend(result)

    groups: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for item in sorted(candidates, key=lambda entry: (-_score(normalized, entry["name"], entry["provider"], entry), entry["name"])):
        if not has_airport_context(normalized) and has_airport_context(item["name"]):
            continue
        if (
            item.get("is_station") is True
            and exact_location_key(item["name"]) == exact_location_key(base_query)
            and any(token in exact_location_key(normalized).split() for token in {"hbf", "hauptbahnhof"})
        ):
            item = {**item, "name": normalized}
        key = (item["provider"], item["provider_id"])
        if key in seen: continue
        seen.add(key)
        group = next((entry for entry in groups if (
            (_distance_km(entry, item) is not None and _distance_km(entry, item) <= 0.75)
            or (_distance_km(entry, item) is None and exact_location_key(entry["name"]) == exact_location_key(item["name"]))
        )), None)
        if group:
            provider = item["provider"]
            group["provider_ids"].setdefault(provider, item["provider_id"])
            aliases = group.setdefault("provider_alias_ids", {}).setdefault(provider, [])
            if item["provider_id"] not in aliases:
                aliases.append(item["provider_id"])
            for field in ("region", "country", "latitude", "longitude"):
                if group.get(field) is None and item.get(field) is not None: group[field] = item[field]
            continue
        groups.append({
            **item,
            "provider_ids": {item["provider"]: item["provider_id"]},
            "provider_alias_ids": {item["provider"]: [item["provider_id"]]},
        })

    ranked: list[dict[str, Any]] = []
    for item in groups[:min(max(limit, 1), 20)]:
        detail = ", ".join(str(part) for part in (item.get("region"), item.get("country")) if part)
        ranked.append({**item, "label": f"{item['name']} — {detail}" if detail else item["name"], "id": f"{item['provider']}:{item['provider_id']}"})
    scores = [_score(normalized, item["name"], item["provider"], item) for item in ranked]
    for item, score in zip(ranked, scores):
        item["type"] = "airport" if "airport" in location_key(item["name"]).split() or "flughafen" in location_key(item["name"]).split() else "station"
        item["confidence"] = round(min(0.99, max(0.01, score / 1050)), 2)
    explicit_station = any(token in exact_location_key(normalized).split() for token in {"hbf", "hauptbahnhof", "bahnhof", "station", "zob", "terminal", "airport", "flughafen"})
    auto = ranked[0] if ranked and explicit_station else None
    return {
        "query": normalized, "stations": ranked, "provider_status": statuses,
        "requires_selection": bool(ranked and not auto),
        "auto_selection": auto,
    }


async def search_stations(query: str, limit: int = 12) -> dict[str, Any]:
    normalized = " ".join(str(query or "").split())
    key = {"generation": APP_VERSION, "ranking": _RANKING_GENERATION, "exact_query": exact_location_key(normalized), "alias_query": location_key(normalized), "limit": limit}
    return await cached_call("locations.resolve", key, _CACHE_TTL, lambda: _search_uncached(normalized, limit))
