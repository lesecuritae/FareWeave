from __future__ import annotations

import asyncio
from datetime import date, timedelta
from typing import Any

from .cache import begin_scope, end_scope, get_cached_journey, save_journey, stats as cache_stats
from .compare import compare_ground_round_trip
from .config import TRIP_TIMEOUT, today_iso
from .models import TripRequest
from .planner import complete_trip
from .presentation import public_result


def _ground_return_date(request: TripRequest) -> tuple[str | None, int | None]:
    if request.journey_type == "one_way":
        return None, 0
    if request.return_mode == "date":
        return request.return_date, None
    return None, request.stay_nights


async def _compute(request: TripRequest) -> dict[str, Any]:
    if request.travel_mode == "ground":
        return_date, stay_nights = _ground_return_date(request)
        try:
            return await asyncio.wait_for(compare_ground_round_trip(
                origin=request.origin,
                destination=request.destination,
                outbound_date=request.departure_date,
                return_date=return_date,
                stay_nights=stay_nights,
                departure_after=request.departure_after,
                preference="cheapest" if request.effective_feeder_preference == "dticket_first" else request.effective_feeder_preference,
                include_flixtrain=request.include_flixtrain,
                include_flixbus=request.include_flixbus,
                max_transfers=None,
                max_results=request.max_results,
                split_ticket_check=request.split_ticket_check,
                deutschlandticket_mode="only" if request.deutschlandticket_only else ("include" if request.deutschlandticket else "exclude"),
                split_candidates=request.feeder_split_candidates,
                one_way=request.journey_type == "one_way",
            ), timeout=TRIP_TIMEOUT)
        except TimeoutError:
            return {
                "status": "partial",
                "search_mode": "ground_trip",
                "current_date": today_iso(),
                "error": f"Die Bahn-/Bus-Reise hat das Gesamtzeitlimit von {TRIP_TIMEOUT} Sekunden erreicht.",
            }

    try:
        return await asyncio.wait_for(complete_trip(request), timeout=TRIP_TIMEOUT)
    except TimeoutError:
        return {
            "status": "partial",
            "search_mode": "trip_plan",
            "current_date": today_iso(),
            "error": f"Die vollständige Reisekette hat das Zeitlimit von {TRIP_TIMEOUT} Sekunden erreicht.",
        }


async def search(request: TripRequest) -> dict[str, Any]:
    token = begin_scope(refresh=request.refresh_cache)
    try:
        if not request.refresh_cache and not request.include_hotel:
            cached = await get_cached_journey(request)
            if cached is not None:
                journey_id, result = cached
                result = {**result, "journey_id": journey_id, "cache": {**cache_stats(), "journey_hit": True}}
                return public_result(result)

        result = await _compute(request)
        if result.get("status") not in {"missing_fields", "needs_clarification"} and not request.include_hotel:
            journey_id = await save_journey(request, result)
            result = {**result, "journey_id": journey_id}
        result["cache"] = {**cache_stats(), "journey_hit": False}
        return public_result(result)
    finally:
        end_scope(token)
