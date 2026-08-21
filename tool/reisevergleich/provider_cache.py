from __future__ import annotations

from typing import Any

from .cache import cached_call
from .config import APP_VERSION
from . import db as raw_db
from . import transitous as raw_transitous
from . import trvl as raw_trvl
from . import gtfs_flix

CACHE_GENERATION = APP_VERSION
DB_TTL = 600
SPLIT_TTL = 600
FLIX_TTL = 600
FLIGHT_TTL = 600
HOTEL_TTL = 900
TRANSFER_TTL = 1800
TRANSITOUS_TTL = 1800


def _key(value: Any) -> dict[str, Any]:
    return {"generation": CACHE_GENERATION, "value": value}


async def db_search_with_retry(**kwargs: Any):
    return await cached_call("db.search", _key(kwargs), DB_TTL, lambda: raw_db.db_search_with_retry(**kwargs))


async def db_split_analysis(analysis_token: str):
    return await cached_call("db.split", _key({"analysis_token": analysis_token}), SPLIT_TTL, lambda: raw_db.db_split_analysis(analysis_token))


async def transitous_search(request, *, deutschlandticket_only: bool = False):
    key = _key({"request": request, "deutschlandticket_only": deutschlandticket_only})
    return await cached_call("transitous.search", key, TRANSITOUS_TTL, lambda: raw_transitous.search(request, deutschlandticket_only=deutschlandticket_only))


async def flix_search(request):
    return await cached_call("gtfs.flix", _key(request), FLIX_TTL, lambda: gtfs_flix.search(request))


async def flight_search(request):
    return await cached_call("trvl.flight", _key(request), FLIGHT_TTL, lambda: raw_trvl.flight_search(request))


async def hotel_search(request):
    # Live accommodation offers are intentionally not persisted. Stay22 permits
    # instant consumer display but no hard/cold storage of its listings.
    return await raw_trvl.hotel_search(request)


async def airport_transfer_search(*args, **kwargs):
    key = _key({"args": args, "kwargs": kwargs})
    return await cached_call("trvl.transfer.outbound", key, TRANSFER_TTL, lambda: raw_trvl.airport_transfer_search(*args, **kwargs))


async def return_transfer_search(*args, **kwargs):
    key = _key({"args": args, "kwargs": kwargs})
    return await cached_call("trvl.transfer.return", key, TRANSFER_TTL, lambda: raw_trvl.return_transfer_search(*args, **kwargs))
