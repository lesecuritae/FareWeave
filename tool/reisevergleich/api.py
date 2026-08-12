from __future__ import annotations

import asyncio
from typing import Any

import httpx
from fastapi import APIRouter

from .airports import AIRPORT_CITY_NAMES, AIRPORT_STATIONS
from .cache import health as cache_health
from .config import APP_VERSION, DB_API_URL, TRANSITOUS_URL, TRANSITOUS_USER_AGENT, today_iso
from .models import TripRequest
from .service import search
from .trvl import capability_report

router = APIRouter()


@router.post(
    "/api/search",
    operation_id="search_trip",
    summary="Reise deterministisch suchen und vergleichen",
)
async def search_trip(request: TripRequest) -> dict[str, Any]:
    return await search(request)


@router.get("/api/config")
async def config() -> dict[str, Any]:
    return {
        "version": APP_VERSION,
        "current_date": today_iso(),
        "defaults": {
            "duration_value": 7,
            "duration_unit": "nights",
            "hotel_property_type": "hotel",
            "hotel_min_stars": 3,
            "airport_buffer_minutes": 120,
            "max_results": 3,
        },
        "airport_cities": AIRPORT_CITY_NAMES,
        "airport_stations": AIRPORT_STATIONS,
    }


@router.get("/api/health")
async def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "version": APP_VERSION,
        "current_date": today_iso(),
        "architecture": "deterministic",
        "providers": ["DB/db-vendo", "Transitous", "Flix", "trvl"],
    }


@router.get("/api/diagnostics")
async def diagnostics() -> dict[str, Any]:
    transitous_probe_url = f"{TRANSITOUS_URL}/api/v1/geocode"
    headers = {"User-Agent": TRANSITOUS_USER_AGENT, "Accept": "application/json"}

    async def probe_db() -> dict[str, Any]:
        try:
            async with httpx.AsyncClient(timeout=20) as client:
                response = await client.get(f"{DB_API_URL}/health")
                return {"ok": response.is_success, "http_status": response.status_code}
        except Exception as exc:
            return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}

    async def probe_transitous() -> dict[str, Any]:
        try:
            async with httpx.AsyncClient(timeout=20, headers=headers, follow_redirects=True) as client:
                response = await client.get(
                    transitous_probe_url,
                    params={"text": "Frankfurt(Main)Hbf", "type": "STOP", "language": "de", "numResults": 1},
                )
                return {"ok": response.is_success, "http_status": response.status_code}
        except Exception as exc:
            return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}

    db, transitous, trvl, cache = await asyncio.gather(
        probe_db(), probe_transitous(), capability_report(), cache_health()
    )
    required = bool(
        db.get("ok")
        and transitous.get("ok")
        and cache.get("status") == "ok"
        and all(item.get("ok") for item in trvl.values())
    )
    return {
        "status": "ok" if required else "degraded",
        "version": APP_VERSION,
        "db_api": db,
        "transitous": transitous,
        "trvl": trvl,
        "cache": cache,
    }
