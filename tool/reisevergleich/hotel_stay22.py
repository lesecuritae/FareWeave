from __future__ import annotations

import os
import time
from datetime import date
from typing import Any

from curl_cffi import requests

from .config import HOTEL_STAY22_TIMEOUT, MAX_HOTEL_TOTAL_EUR
from .models import HotelRequest
from .utils import as_float, as_int

STAY22_URL = os.getenv("STAY22_API_URL", "https://api.stay22.com/v2/accommodations")
_ALLOWED_SUPPLIERS = ("expedia", "hotelscom")
_PROPERTY_TYPES = {
    "hotel": "hotel",
    "resort": "resort",
    "apartment": "apartment",
    "hostel": "hostel",
    "bnb": "bed_and_breakfast",
    "villa": "villa",
}


def _stay_nights(request: HotelRequest) -> int:
    return (date.fromisoformat(request.checkout_date) - date.fromisoformat(request.checkin_date)).days


def parse_stay22_options(data: Any, request: HotelRequest) -> list[dict[str, Any]]:
    if not isinstance(data, dict):
        return []
    meta = data.get("meta") if isinstance(data.get("meta"), dict) else {}
    currency = str(meta.get("currency") or "").upper()
    if (
        meta.get("checkin") != request.checkin_date
        or meta.get("checkout") != request.checkout_date
        or as_int(meta.get("nights")) != _stay_nights(request)
        or currency != "EUR"
    ):
        return []

    output: list[dict[str, Any]] = []
    for item in data.get("results") or []:
        if not isinstance(item, dict):
            continue
        rating = item.get("rating") if isinstance(item.get("rating"), dict) else {}
        stars = as_int(rating.get("hotelStars"))
        if stars and request.min_stars > 0 and stars < request.min_stars:
            continue

        suppliers = item.get("suppliers") if isinstance(item.get("suppliers"), dict) else {}
        offers: list[tuple[float, str, str]] = []
        for provider in _ALLOWED_SUPPLIERS:
            source = suppliers.get(provider)
            if not isinstance(source, dict):
                continue
            price = source.get("price") if isinstance(source.get("price"), dict) else {}
            total = as_float(price.get("total"))
            link = str(source.get("link") or "").strip()
            if 0 < total <= MAX_HOTEL_TOTAL_EUR and link.startswith("https://"):
                offers.append((total, provider, link))
        if not offers:
            continue

        total, provider, link = min(offers, key=lambda offer: offer[0])
        location = item.get("location") if isinstance(item.get("location"), dict) else {}
        option = {
            "name": item.get("name"),
            "rating": as_float(rating.get("value")) or None,
            "review_count": as_int(rating.get("count")) or None,
            "stars": stars or None,
            "provider_min_stars": request.min_stars or None,
            "property_type": request.property_type,
            "address": location.get("address"),
            "verified_total_price": round(total, 2),
            "currency": currency,
            "price_basis": "total_stay",
            "price_confidence": "provider_total",
            "booking_url": link,
            "provider": f"stay22:{provider}",
            "freshness": "live",
        }
        output.append({key: value for key, value in option.items() if value not in (None, "", [])})

    output.sort(key=lambda item: (as_float(item.get("verified_total_price")), str(item.get("name") or "")))
    return output[: max(request.max_results * 4, request.max_results)]


def search_stay22_sync(request: HotelRequest) -> dict[str, Any]:
    params: dict[str, Any] = {
        "address": request.location,
        "provider": ",".join(_ALLOWED_SUPPLIERS),
        "checkin": request.checkin_date,
        "checkout": request.checkout_date,
        "adults": request.adults,
        "children": 0,
        "rooms": 1,
        "currency": "EUR",
        "pageSize": min(max(request.max_results * 8, 12), 100),
        "lang": "en",
    }
    property_type = _PROPERTY_TYPES.get(request.property_type)
    if property_type:
        params["type"] = property_type
    if request.min_stars > 0:
        params["minstarrating"] = request.min_stars
    if request.min_rating is not None:
        params["minguestrating"] = request.min_rating

    headers = {"Accept": "application/json"}
    api_key = os.getenv("STAY22_API_KEY", "").strip()
    if api_key:
        headers["X-API-KEY"] = api_key

    started = time.monotonic()
    try:
        response = requests.get(
            STAY22_URL,
            params=params,
            headers=headers,
            impersonate="firefox",
            timeout=HOTEL_STAY22_TIMEOUT,
            allow_redirects=True,
        )
        elapsed_ms = round((time.monotonic() - started) * 1000)
        if response.status_code != 200:
            return {
                "options": [],
                "status": {
                    "provider": "stay22_expedia_hotelscom",
                    "ok": False,
                    "timed_out": False,
                    "http_status": response.status_code,
                    "result_count": 0,
                    "elapsed_ms": elapsed_ms,
                },
            }
        options = parse_stay22_options(response.json(), request)
        return {
            "options": options,
            "status": {
                "provider": "stay22_expedia_hotelscom",
                "ok": True,
                "timed_out": False,
                "result_count": len(options),
                "elapsed_ms": elapsed_ms,
            },
        }
    except Exception as exc:
        elapsed_ms = round((time.monotonic() - started) * 1000)
        return {
            "options": [],
            "status": {
                "provider": "stay22_expedia_hotelscom",
                "ok": False,
                "timed_out": "timeout" in type(exc).__name__.casefold() or "timeout" in str(exc).casefold(),
                "result_count": 0,
                "elapsed_ms": elapsed_ms,
                "error": f"{type(exc).__name__}: {exc}",
            },
        }
