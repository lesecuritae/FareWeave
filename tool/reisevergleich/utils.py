from __future__ import annotations

import json
import re
import subprocess
from datetime import datetime
from typing import Any
from urllib.parse import quote, urlencode

from .config import TZ


def as_float(value: Any) -> float:
    if isinstance(value, dict):
        value = value.get("amount") or value.get("total") or value.get("value")
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def as_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def parse_datetime(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=TZ)


def route_departure_in_window(
    route: dict[str, Any], travel_date: str, departure_after: str,
) -> bool:
    """Return whether a normalized route departs at/after the local request floor."""
    departure = route.get("departure")
    if isinstance(departure, dict):
        departure = departure.get("time")
    parsed = parse_datetime(departure)
    if not parsed:
        return False
    floor = datetime.fromisoformat(f"{travel_date}T{departure_after}:00").replace(tzinfo=TZ)
    return parsed.astimezone(TZ) >= floor


def local_iso(value: Any) -> str | None:
    parsed = parse_datetime(value)
    if parsed is None:
        return str(value) if isinstance(value, str) and value else None
    return parsed.astimezone(TZ).isoformat(timespec="minutes")


def local_clock(value: Any) -> str | None:
    parsed = parse_datetime(value)
    return parsed.astimezone(TZ).strftime("%H:%M") if parsed else None


def run_command(command: list[str], timeout: int) -> dict[str, Any]:
    try:
        completed = subprocess.run(
            command,
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
        return {
            "ok": completed.returncode == 0,
            "code": completed.returncode,
            "stdout": completed.stdout.strip(),
            "stderr": completed.stderr.strip(),
            "command": command,
        }
    except subprocess.TimeoutExpired:
        return {"ok": False, "code": 124, "stdout": "", "stderr": "Zeitüberschreitung", "command": command}
    except FileNotFoundError as exc:
        return {"ok": False, "code": 127, "stdout": "", "stderr": str(exc), "command": command}


def run_json_command(command: list[str], timeout: int) -> dict[str, Any]:
    result = run_command(command, timeout)
    if not result["ok"]:
        return {"ok": False, "error": result.get("stderr") or result.get("stdout"), "raw": result}
    raw = result.get("stdout") or ""
    try:
        return {"ok": True, "data": json.loads(raw), "raw": result}
    except json.JSONDecodeError:
        starts = [position for position in (raw.find("{"), raw.find("[")) if position >= 0]
        end = max(raw.rfind("}"), raw.rfind("]"))
        if starts and end > min(starts):
            try:
                return {"ok": True, "data": json.loads(raw[min(starts): end + 1]), "raw": result}
            except json.JSONDecodeError:
                pass
        return {"ok": False, "error": "JSON-Ausgabe konnte nicht gelesen werden", "raw": result}


def build_google_flights_url(origin: str, destination: str, departure: str, return_date: str | None = None) -> str:
    query = f"Flights from {origin} to {destination} on {departure}"
    if return_date:
        query += f" returning {return_date}"
    return "https://www.google.com/travel/flights?" + urlencode({"q": query}, quote_via=quote)


def build_google_hotels_url(location: str, checkin: str, checkout: str) -> str:
    query = f"Hotels in {location} from {checkin} to {checkout}"
    return "https://www.google.com/travel/hotels?" + urlencode({"q": query}, quote_via=quote)


def build_google_maps_url(origin: str, destination: str) -> str:
    return "https://www.google.com/maps/dir/?" + urlencode({"api": "1", "origin": origin, "destination": destination})


def normalize_text(value: str) -> str:
    value = value.casefold().replace("hauptbahnhof", "hbf")
    return re.sub(r"[^a-z0-9äöüß]+", " ", value).strip()
