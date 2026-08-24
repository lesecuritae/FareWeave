from __future__ import annotations

import re
import unicodedata


# Deliberately small, explicit translation table.  It is used only after an
# exact provider lookup failed; provider station IDs and names remain primary.
CITY_ALIASES = {
    "munchen": "munich", "muenchen": "munich",
    "koln": "cologne", "koeln": "cologne",
    "wien": "vienna",
    "nurnberg": "nuremberg", "nuernberg": "nuremberg",
    "hannover": "hanover", "braunschweig": "brunswick",
    "zuerich": "zurich", "genf": "geneva", "prag": "prague",
    "warschau": "warsaw", "krakau": "krakow", "danzig": "gdansk",
    "breslau": "wroclaw", "posen": "poznan", "mailand": "milan",
    "florenz": "florence", "venedig": "venice", "neapel": "naples", "rom": "rome",
    "genua": "genoa", "brussel": "brussels", "bruessel": "brussels",
    "antwerpen": "antwerp", "kopenhagen": "copenhagen",
    "lissabon": "lisbon", "sevilla": "seville", "athen": "athens",
    "bukarest": "bucharest", "saloniki": "thessaloniki",
    "laibach": "ljubljana", "agram": "zagreb", "pressburg": "bratislava",
}

AIRPORT_WORDS = {"airport", "flughafen", "aeroport", "terminal"}

CENTRAL_STATIONS = {
    "munich": "München Hbf",
    "cologne": "Köln Hbf",
    "zurich": "Zürich HB",
    "vienna": "Wien Hbf",
    "prague": "Praha hlavní nádraží",
    "milan": "Milano Centrale",
    "rome": "Roma Termini",
}


def exact_location_key(value: str | None) -> str:
    return " ".join(re.findall(r"[^\W_]+", str(value or "").casefold(), flags=re.UNICODE))


def _alias_source_key(value: str | None) -> str:
    text = unicodedata.normalize("NFKD", str(value or "").casefold())
    text = "".join(char for char in text if not unicodedata.combining(char))
    return " ".join(re.findall(r"[a-z0-9]+", text))


def location_key(value: str | None) -> str:
    """Comparable key with conservative international city aliases."""
    return " ".join(CITY_ALIASES.get(token, token) for token in _alias_source_key(value).split())


def has_airport_context(value: str | None) -> bool:
    text = str(value or "").strip()
    tokens = set(exact_location_key(text).split())
    return bool(re.fullmatch(r"[A-Z]{3}", text) or AIRPORT_WORDS.intersection(tokens))


def location_candidates(value: str | None) -> tuple[str, ...]:
    """Exact user text first, translated city spelling only as fallback."""
    text = str(value or "").strip()
    if not text or has_airport_context(text):
        return (text,)
    translated = location_key(text)
    canonical = CENTRAL_STATIONS.get(translated) if len(exact_location_key(text).split()) == 1 else None
    translated_fallback = translated if exact_location_key(translated) != exact_location_key(text) else None
    return tuple(dict.fromkeys(candidate for candidate in (text, canonical, translated_fallback) if candidate))


def location_match_is_safe(requested: str, resolved: str | None) -> bool:
    """Reject an ambiguous city hit until its canonical station fallback runs."""
    translated = location_key(requested)
    canonical = CENTRAL_STATIONS.get(translated) if len(exact_location_key(requested).split()) == 1 else None
    if not canonical:
        return True
    resolved_key = location_key(resolved)
    canonical_tokens = set(location_key(canonical).split())
    return bool(resolved_key == location_key(canonical) or canonical_tokens <= set(resolved_key.split()))
