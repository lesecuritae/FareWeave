from __future__ import annotations

import os
from datetime import datetime
from zoneinfo import ZoneInfo

TZ = ZoneInfo(os.getenv("APP_TIMEZONE", "Europe/Berlin"))


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}
APP_VERSION = "0.0.3"
DB_API_URL = os.getenv("DB_API_URL", "http://db-api:3001").rstrip("/")
TRANSITOUS_URL = os.getenv("TRANSITOUS_URL", "https://api.transitous.org").rstrip("/")
TRANSITOUS_USER_AGENT = os.getenv("TRANSITOUS_USER_AGENT", "fareweave/0.0.3")
TRVL_BIN = os.getenv("TRVL_BIN", "trvl")

# Harte Obergrenzen pro externer Quelle. Kein einzelner Anbieter darf die
# Gesamtreise blockieren. Die Werte bleiben absichtlich deutlich unter dem
# globalen Reise-Timeout.
FLIGHT_PROVIDER_TIMEOUT = min(max(int(os.getenv("FLIGHT_PROVIDER_TIMEOUT", "25")), 8), 45)
FLIGHT_PROVIDER_CONCURRENCY = min(max(int(os.getenv("FLIGHT_PROVIDER_CONCURRENCY", "3")), 1), 4)
HOTEL_ENRICH_TIMEOUT = min(max(int(os.getenv("HOTEL_ENRICH_TIMEOUT", "35")), 15), 55)
HOTEL_HEADLINE_TIMEOUT = min(max(int(os.getenv("HOTEL_HEADLINE_TIMEOUT", "20")), 8), 35)
HOTEL_STAY22_TIMEOUT = min(max(int(os.getenv("HOTEL_STAY22_TIMEOUT", "15")), 6), 25)
GROUND_PROVIDER_TIMEOUT = min(max(int(os.getenv("GROUND_PROVIDER_TIMEOUT", "22")), 8), 40)
GROUND_PROVIDER_CONCURRENCY = min(max(int(os.getenv("GROUND_PROVIDER_CONCURRENCY", "2")), 1), 3)
TRANSFER_PROVIDER_TIMEOUT = min(max(int(os.getenv("TRANSFER_PROVIDER_TIMEOUT", "20")), 8), 35)
TRANSFER_PROVIDER_CONCURRENCY = min(max(int(os.getenv("TRANSFER_PROVIDER_CONCURRENCY", "2")), 1), 3)
TRANSITOUS_TIMEOUT = min(max(int(os.getenv("TRANSITOUS_TIMEOUT", "25")), 8), 40)
DB_SEARCH_TIMEOUT = min(max(int(os.getenv("DB_SEARCH_TIMEOUT", "50")), 20), 75)
DB_SPLIT_TIMEOUT = min(max(int(os.getenv("DB_SPLIT_TIMEOUT", "45")), 15), 70)
TRIP_TIMEOUT = min(max(int(os.getenv("TRIP_TIMEOUT", "210")), 90), 360)
HISTORY_ENABLED = _env_bool("HISTORY_ENABLED", True)
HISTORY_CACHE_DIR = os.getenv("HISTORY_CACHE_DIR", "/var/lib/reisevergleich/history")
HISTORY_CACHE_MAX_GB = min(max(float(os.getenv("HISTORY_CACHE_MAX_GB", "5")), 0.1), 100.0)
HISTORY_REMOTE_TIMEOUT = min(max(float(os.getenv("HISTORY_REMOTE_TIMEOUT", "60")), 2.0), 120.0)
HISTORY_MAX_CONCURRENCY = min(max(int(os.getenv("HISTORY_MAX_CONCURRENCY", "2")), 1), 4)
HISTORY_STATS_TTL = min(max(int(os.getenv("HISTORY_STATS_TTL", "86400")), 300), 31_536_000)
HISTORY_DEFAULT_WINDOW_DAYS = min(max(int(os.getenv("HISTORY_DEFAULT_WINDOW_DAYS", "90")), 7), 730)
HISTORY_SOURCE_REVISION = os.getenv("HISTORY_SOURCE_REVISION", "main").strip() or "main"


def today_iso() -> str:
    return datetime.now(TZ).date().isoformat()


# Grenzen gegen übergroße oder offensichtlich fehlerhafte Providerwerte.
MAX_HOTEL_NIGHTLY_EUR = float(os.getenv("MAX_HOTEL_NIGHTLY_EUR", "20000"))
MAX_HOTEL_TOTAL_EUR = float(os.getenv("MAX_HOTEL_TOTAL_EUR", "100000"))
MAX_FLIGHT_PACKAGES = min(max(int(os.getenv("MAX_FLIGHT_PACKAGES", "2")), 1), 3)
MAX_RETURN_DATE_PROBES = min(max(int(os.getenv("MAX_RETURN_DATE_PROBES", "2")), 1), 3)
MAX_FEEDER_HANDOFFS = min(max(int(os.getenv("MAX_FEEDER_HANDOFFS", "2")), 1), 4)
MAX_FLIX_FEEDER_TARGETS = min(max(int(os.getenv("MAX_FLIX_FEEDER_TARGETS", "3")), 1), 5)
MAX_FLIX_FEEDER_DISCOVERED = min(max(int(os.getenv("MAX_FLIX_FEEDER_DISCOVERED", "2")), 0), 3)
