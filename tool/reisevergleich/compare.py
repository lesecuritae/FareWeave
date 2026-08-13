from __future__ import annotations

import asyncio
from datetime import date, datetime, timedelta
from typing import Any

from .config import TZ, today_iso
from .db import build_manual_db_links, compact_attempts, compact_route, rank_routes
from .models import DeutschlandticketRequest, ReiseRequest
from .provider_cache import db_search_with_retry, db_split_analysis, flix_search, transitous_search
from .ground_mixed import ground_mixed_options
from .history import enrich_routes_history
from .utils import as_float, as_int, parse_datetime

def _route_departure_in_window(route: dict[str, Any], travel_date: str, departure_after: str) -> bool:
    departure = route.get("departure")
    if isinstance(departure, dict):
        departure = departure.get("time")
    parsed = parse_datetime(departure)
    if not parsed:
        return False
    floor = datetime.fromisoformat(f"{travel_date}T{departure_after}:00").replace(tzinfo=TZ)
    return parsed.astimezone(TZ) >= floor


def _compact_split(split: dict[str, Any]) -> dict[str, Any]:
    output = {
        "status": split.get("status"),
        "method": split.get("method"),
        "original_price": split.get("original_price"),
        "currency": split.get("currency"),
        "checked_split_points": split.get("checked_split_points"),
        "reason": split.get("reason"),
        "error": split.get("error"),
    }
    options = split.get("split_options")
    if isinstance(options, list) and options:
        output["split_options"] = options[:3]
    return {key: value for key, value in output.items() if value not in (None, "", [])}


async def compare_trip(request: ReiseRequest) -> dict[str, Any]:
    db_task = asyncio.create_task(db_search_with_retry(
        origin=request.origin,
        destination=request.destination,
        travel_date=request.travel_date,
        departure_after=request.departure_after,
        mode="all",
        max_transfers=request.max_transfers,
        results=request.max_results,
    ))
    # Fallbacks parallel starten: Wenn DBnav/DB langsam ist, ist Transitous bereits
    # unterwegs. Flix läuft ebenfalls unabhängig und kann die Bahn nie blockieren.
    transitous_task = asyncio.create_task(transitous_search(request))
    flix_task = asyncio.create_task(flix_search(request))

    try:
        db_result, db_attempts = await db_task
    except Exception as exc:
        db_result = {"status": "failed", "journeys": []}
        db_attempts = [{"source": "db-api", "attempt": 1, "ok": False, "error": f"{type(exc).__name__}: {exc}"}]

    try:
        transitous_result = await transitous_task
    except Exception as exc:
        transitous_result = {"routes": [], "diagnostic": {"ok": False, "error": f"{type(exc).__name__}: {exc}"}}

    try:
        flix_result = await flix_task
    except Exception as exc:
        flix_result = {"routes": [], "provider_status": {"provider": "flixbus", "ok": False, "error": f"{type(exc).__name__}: {exc}"}}

    db_routes = db_result.get("journeys") or []
    db_source = db_result.get("source")
    transitous_diagnostic = transitous_result.get("diagnostic")
    if not db_routes:
        db_routes = transitous_result.get("routes") or []
        if db_routes:
            db_source = "transitous"

    db_routes = [route for route in db_routes if _route_departure_in_window(route, request.travel_date, request.departure_after)]

    flix_routes = flix_result.get("routes") or []
    flix_routes = [route for route in flix_routes if _route_departure_in_window(route, request.travel_date, request.departure_after)]

    # Historie ist eine unabhängige, rein additive Schicht. Fehler oder Timeouts
    # dürfen Providerresultate, Preise und Ranking niemals verändern.
    try:
        db_routes = await enrich_routes_history(db_routes)
    except Exception:
        pass

    selected_db = rank_routes(db_routes, request.preference)[0] if db_routes else None
    split: dict[str, Any] = {
        "status": "skipped",
        "method": "db-vendo-direct-two-ticket",
        "reason": "Keine DB- oder DBnav-Verbindung mit Live-Preis und Analyse-Token verfügbar.",
    }
    if (
        request.split_ticket_check and selected_db
        and selected_db.get("db_source") in {"db", "dbnav"}
        and selected_db.get("analysis_token")
        and as_float(selected_db.get("price")) > 0
    ):
        try:
            split = await db_split_analysis(str(selected_db["analysis_token"]))
        except Exception as exc:
            split = {
                "status": "failed",
                "method": "db-vendo-direct-two-ticket",
                "error": f"{type(exc).__name__}: {exc}",
                "split_options": [],
            }

    if split.get("status") == "success" and selected_db:
        options = split.get("split_options") or []
        if options:
            selected_db = dict(selected_db)
            selected_db["best_split_price"] = options[0].get("total_price")
            selected_db["split_savings"] = options[0].get("savings")
            db_routes = [
                selected_db if route.get("id") == selected_db.get("id") else route
                for route in db_routes
            ]

    ranked_db = rank_routes(db_routes, request.preference)
    combined = rank_routes(db_routes + flix_routes, request.preference)
    priced = [route for route in combined if as_float(route.get("price")) > 0]
    fastest = min(combined, key=lambda route: as_int(route.get("duration_minutes")) or 1_000_000, default=None)

    has_db_price = any(
        route.get("db_source") in {"db", "dbnav"} and as_float(route.get("price")) > 0
        for route in db_routes
    )
    manual_links = build_manual_db_links(
        request.origin, request.destination, request.travel_date, request.departure_after,
        departure_iso=(str(ranked_db[0].get("departure")) if ranked_db else None),
    )

    warnings: list[str] = []
    if not has_db_price:
        warnings.append("Kein belastbarer DB-Livepreis verfügbar; vorhandene Bahnzeiten können aus dem Fallback stammen.")
    if flix_routes:
        warnings.append("Flix-Preise vor der Buchung auf der Anbieterseite bestätigen.")
    if split.get("status") == "no_saving_found":
        warnings.append("Die interne Zwei-Ticket-Prüfung wurde durchgeführt und fand keine Ersparnis.")
    elif split.get("status") in {"failed", "unavailable", "skipped"}:
        warnings.append("Die interne Zwei-Ticket-Prüfung konnte für diese Verbindung nicht vollständig ausgewertet werden.")

    return {
        "status": "ok" if combined else "manual_required",
        "search_mode": "price_compare",
        "current_date": today_iso(),
        "query": request.model_dump(),
        "db_source": db_source,
        "source_status": {
            "db_live_price_available": has_db_price,
            "db_attempts": compact_attempts(db_attempts),
            "transitous": transitous_diagnostic,
            "flix": flix_result.get("provider_status"),
        },
        "db_options": [compact_route(route) for route in ranked_db[:3]],
        "flix_options": flix_routes[:3],
        "recommendation": {
            "fastest": compact_route(fastest) if isinstance(fastest, dict) and fastest.get("db_source") else fastest,
            "cheapest_with_live_price": compact_route(priced[0]) if priced and priced[0].get("db_source") else (priced[0] if priced else None),
        },
        "manual_db_links": manual_links,
        "split_ticket": _compact_split(split),
        "warnings": warnings,
    }


async def deutschlandticket(request: DeutschlandticketRequest) -> dict[str, Any]:
    db_task = asyncio.create_task(db_search_with_retry(
        origin=request.origin,
        destination=request.destination,
        travel_date=request.travel_date,
        departure_after=request.departure_after,
        mode="deutschlandticket",
        max_transfers=request.max_transfers,
        results=request.max_results,
    ))
    fallback = ReiseRequest(
        origin=request.origin,
        destination=request.destination,
        travel_date=request.travel_date,
        departure_after=request.departure_after,
        preference="fastest",
        include_flixtrain=False,
        include_flixbus=False,
        max_transfers=request.max_transfers,
        max_results=request.max_results,
        split_ticket_check=False,
    )
    transitous_task = asyncio.create_task(transitous_search(fallback, deutschlandticket_only=True))

    try:
        result, attempts = await db_task
    except Exception as exc:
        result = {"status": "failed", "journeys": []}
        attempts = [{"source": "db-api", "attempt": 1, "ok": False, "error": f"{type(exc).__name__}: {exc}"}]
    try:
        transitous_result = await transitous_task
    except Exception as exc:
        transitous_result = {"routes": [], "diagnostic": {"ok": False, "error": f"{type(exc).__name__}: {exc}"}}

    routes = result.get("journeys") or []
    source = result.get("source")
    if not routes:
        routes = transitous_result.get("routes") or []
        if routes:
            source = "transitous"

    try:
        routes = await enrich_routes_history(routes)
    except Exception:
        pass

    return {
        "status": "ok" if routes else "empty",
        "search_mode": "deutschlandticket",
        "current_date": today_iso(),
        "query": request.model_dump(),
        "source": source,
        "attempts": compact_attempts(attempts),
        "routes": [compact_route(route) for route in routes[: request.max_results]],
        "transitous_diagnostic": transitous_result.get("diagnostic"),
        "warning": (
            "Die Suche filtert Fernverkehr heraus, ist aber keine Tarifgarantie. Sonderzüge, einzelne Fähren "
            "und grenzüberschreitende Abschnitte müssen separat geprüft werden."
        ),
    }

def _route_arrival_date(result: dict[str, Any]) -> str | None:
    recommendation = result.get("recommendation") if isinstance(result.get("recommendation"), dict) else {}
    route = recommendation.get("cheapest_with_live_price") or recommendation.get("fastest")
    if not isinstance(route, dict):
        return None
    value = route.get("arrival")
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).date().isoformat()
    except ValueError:
        return None



def _recommended_live_price(result: dict[str, Any]) -> float:
    recommendation = result.get("recommendation") if isinstance(result.get("recommendation"), dict) else {}
    route = recommendation.get("cheapest_with_live_price")
    if not isinstance(route, dict):
        return 0.0
    return as_float(route.get("price"))

def _direction_summary(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": result.get("status"),
        "query": result.get("query"),
        "db_source": result.get("db_source"),
        "db_options": result.get("db_options") or [],
        "flix_options": result.get("flix_options") or [],
        "recommendation": result.get("recommendation"),
        "split_ticket": result.get("split_ticket"),
        "manual_db_links": result.get("manual_db_links"),
        "warnings": result.get("warnings") or [],
    }


async def compare_ground_round_trip(
    *,
    origin: str,
    destination: str,
    outbound_date: str,
    return_date: str | None,
    stay_nights: int | None,
    departure_after: str,
    preference: str,
    include_flixtrain: bool,
    include_flixbus: bool,
    max_transfers: int | None,
    max_results: int,
    split_ticket_check: bool,
    deutschlandticket_mode: str | None = None,
    split_candidates: list[str] | None = None,
    one_way: bool = False,
) -> dict[str, Any]:
    if deutschlandticket_mode == "only":
        outward_dt = await deutschlandticket(DeutschlandticketRequest(
            origin=origin, destination=destination, travel_date=outbound_date,
            departure_after=departure_after, max_transfers=max_transfers, max_results=max_results,
        ))
        outward_routes = outward_dt.get("routes") or []
        if one_way:
            complete = bool(outward_routes)
            return {
                "status": "ok" if complete else "partial",
                "search_mode": "ground_trip",
                "current_date": today_iso(),
                "route": {
                    "origin": origin, "destination": destination, "outbound_date": outbound_date,
                    "return_date": None, "return_date_source": None, "stay_nights": 0,
                },
                "trip_chain": ["outbound_ground"],
                "outbound": {"status": outward_dt.get("status"), "db_options": [], "flix_options": [], "mixed_ticket_options": [], "recommendation": None, "split_ticket": {"status": "not_applicable"}, "warnings": []},
                "return": None,
                "deutschlandticket": {"outbound": outward_routes, "return": [], "warning": outward_dt.get("warning"), "only": True},
                "price_summary": {
                    "outbound_live_price": 0.0 if complete else None,
                    "return_live_price": None,
                    "round_trip_live_price": None,
                    "known_total_price": 0.0 if complete else None,
                    "currency": "EUR" if complete else None,
                    "complete": complete,
                    "price_semantics": "deutschlandticket_covered_additional_cost",
                },
                "hotel": None,
            }
        return_source = "explicit" if return_date else None
        if not return_date and stay_nights:
            first_outward = (outward_dt.get("routes") or [None])[0]
            arrival_date = _route_arrival_date({"recommendation": {"fastest": first_outward}}) if first_outward else None
            return_date = (date.fromisoformat(arrival_date or outbound_date) + timedelta(days=stay_nights)).isoformat()
            return_source = "stay_duration"
        if not return_date:
            return {
                "status": "missing_fields", "search_mode": "ground_trip", "current_date": today_iso(),
                "missing_fields": ["return_date_or_stay_duration"],
            }
        return_dt = await deutschlandticket(DeutschlandticketRequest(
            origin=destination, destination=origin, travel_date=return_date,
            departure_after=departure_after, max_transfers=max_transfers, max_results=max_results,
        ))
        outward_routes = outward_dt.get("routes") or []
        return_routes = return_dt.get("routes") or []
        complete = bool(outward_routes and return_routes)
        return {
            "status": "ok" if complete else "partial",
            "search_mode": "ground_trip",
            "current_date": today_iso(),
            "route": {
                "origin": origin, "destination": destination, "outbound_date": outbound_date,
                "return_date": return_date, "return_date_source": return_source, "stay_nights": stay_nights,
            },
            "trip_chain": ["outbound_ground", "return_ground"],
            "outbound": {"status": outward_dt.get("status"), "db_options": [], "flix_options": [], "mixed_ticket_options": [], "recommendation": None, "split_ticket": {"status": "not_applicable"}, "warnings": []},
            "return": {"status": return_dt.get("status"), "db_options": [], "flix_options": [], "mixed_ticket_options": [], "recommendation": None, "split_ticket": {"status": "not_applicable"}, "warnings": []},
            "deutschlandticket": {
                "outbound": outward_routes, "return": return_routes,
                "warning": outward_dt.get("warning") or return_dt.get("warning"),
                "only": True,
            },
            "price_summary": {
                "outbound_live_price": 0.0 if outward_routes else None,
                "return_live_price": 0.0 if return_routes else None,
                "round_trip_live_price": 0.0 if complete else None,
                "currency": "EUR" if complete else None,
                "complete": complete,
                "price_semantics": "deutschlandticket_covered_additional_cost",
            },
            "hotel": None,
        }

    outbound_request = ReiseRequest(
        origin=origin,
        destination=destination,
        travel_date=outbound_date,
        departure_after=departure_after,
        preference=preference,
        include_flixtrain=include_flixtrain,
        include_flixbus=include_flixbus,
        max_transfers=max_transfers,
        max_results=max_results,
        split_ticket_check=split_ticket_check,
    )
    outbound = await compare_trip(outbound_request)

    if one_way:
        outbound_mixed: list[dict[str, Any]] = []
        if deutschlandticket_mode == "include" and split_candidates:
            outbound_mixed = await ground_mixed_options(
                origin, destination, outbound_date, departure_after, split_candidates,
                include_flixbus=include_flixbus, include_flixtrain=include_flixtrain,
            )
        dticket: dict[str, Any] | None = None
        if deutschlandticket_mode == "include":
            outward_dt = await deutschlandticket(DeutschlandticketRequest(
                origin=origin, destination=destination, travel_date=outbound_date,
                departure_after=departure_after, max_transfers=max_transfers, max_results=max_results,
            ))
            dticket = {
                "outbound": outward_dt.get("routes") or [],
                "return": [],
                "warning": outward_dt.get("warning"),
            }
        outbound_price = _recommended_live_price(outbound)
        return {
            "status": "ok" if outbound.get("status") in {"ok", "manual_required"} else "partial",
            "search_mode": "ground_trip",
            "current_date": today_iso(),
            "route": {
                "origin": origin, "destination": destination, "outbound_date": outbound_date,
                "return_date": None, "return_date_source": None, "stay_nights": 0,
            },
            "trip_chain": ["outbound_ground"],
            "outbound": {**_direction_summary(outbound), "mixed_ticket_options": outbound_mixed},
            "return": None,
            "deutschlandticket": dticket,
            "price_summary": {
                "outbound_live_price": round(outbound_price, 2) if outbound_price > 0 else None,
                "return_live_price": None,
                "round_trip_live_price": None,
                "known_total_price": round(outbound_price, 2) if outbound_price > 0 else None,
                "currency": "EUR" if outbound_price > 0 else None,
                "complete": bool(outbound_price > 0),
            },
            "hotel": None,
        }

    return_source = "explicit" if return_date else None
    if not return_date and stay_nights:
        anchor = _route_arrival_date(outbound) or outbound_date
        return_date = (date.fromisoformat(anchor) + timedelta(days=stay_nights)).isoformat()
        return_source = "stay_duration"

    if not return_date:
        return {
            "status": "missing_fields",
            "search_mode": "ground_trip",
            "current_date": today_iso(),
            "missing_fields": ["return_date_or_stay_duration"],
            "outbound": _direction_summary(outbound),
        }

    return_request = ReiseRequest(
        origin=destination,
        destination=origin,
        travel_date=return_date,
        departure_after=departure_after,
        preference=preference,
        include_flixtrain=include_flixtrain,
        include_flixbus=include_flixbus,
        max_transfers=max_transfers,
        max_results=max_results,
        split_ticket_check=split_ticket_check,
    )
    return_result = await compare_trip(return_request)
    outbound_mixed: list[dict[str, Any]] = []
    return_mixed: list[dict[str, Any]] = []
    if deutschlandticket_mode == "include" and split_candidates:
        outbound_mixed, return_mixed = await asyncio.gather(
            ground_mixed_options(origin, destination, outbound_date, departure_after, split_candidates, include_flixbus=include_flixbus, include_flixtrain=include_flixtrain),
            ground_mixed_options(destination, origin, return_date, departure_after, list(reversed(split_candidates)), include_flixbus=include_flixbus, include_flixtrain=include_flixtrain),
        )

    dticket: dict[str, Any] | None = None
    if deutschlandticket_mode == "include":
        outward_dt, return_dt = await asyncio.gather(
            deutschlandticket(DeutschlandticketRequest(
                origin=origin, destination=destination, travel_date=outbound_date,
                departure_after=departure_after, max_transfers=max_transfers, max_results=max_results,
            )),
            deutschlandticket(DeutschlandticketRequest(
                origin=destination, destination=origin, travel_date=return_date,
                departure_after=departure_after, max_transfers=max_transfers, max_results=max_results,
            )),
        )
        dticket = {
            "outbound": outward_dt.get("routes") or [],
            "return": return_dt.get("routes") or [],
            "warning": outward_dt.get("warning") or return_dt.get("warning"),
        }

    status = (
        "ok"
        if outbound.get("status") in {"ok", "manual_required"}
        and return_result.get("status") in {"ok", "manual_required"}
        else "partial"
    )
    outbound_price = _recommended_live_price(outbound)
    return_price = _recommended_live_price(return_result)
    price_summary = {
        "outbound_live_price": round(outbound_price, 2) if outbound_price > 0 else None,
        "return_live_price": round(return_price, 2) if return_price > 0 else None,
        "round_trip_live_price": round(outbound_price + return_price, 2) if outbound_price > 0 and return_price > 0 else None,
        "currency": "EUR" if outbound_price > 0 or return_price > 0 else None,
        "complete": bool(outbound_price > 0 and return_price > 0),
    }
    return {
        "status": status,
        "search_mode": "ground_trip",
        "current_date": today_iso(),
        "route": {
            "origin": origin,
            "destination": destination,
            "outbound_date": outbound_date,
            "return_date": return_date,
            "return_date_source": return_source,
            "stay_nights": stay_nights,
        },
        "trip_chain": ["outbound_ground", "return_ground"],
        "outbound": {**_direction_summary(outbound), "mixed_ticket_options": outbound_mixed},
        "return": {**_direction_summary(return_result), "mixed_ticket_options": return_mixed},
        "deutschlandticket": dticket,
        "price_summary": price_summary,
        "hotel": None,
    }
