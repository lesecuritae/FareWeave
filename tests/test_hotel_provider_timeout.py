from pathlib import Path
import os
import re
from reisevergleich.cache import _cacheable_component

root = Path(os.environ.get("SOURCE_ROOT", Path(__file__).resolve().parents[1]))
compose = (root / "compose.yml").read_text(encoding="utf-8")


def env_value(name: str) -> str:
    match = re.search(rf"^\s+{re.escape(name)}:\s*[\"']?([^\"'\n#]+)", compose, re.MULTILINE)
    assert match, f"{name} fehlt in compose.yml"
    return match.group(1).strip()


assert env_value("TRVL_PROVIDER_TIMEOUT") == "8s", (
    "Der interne trvl-Provider-Timeout muss deutlich unter dem 20-Sekunden-"
    "Headline-Limit liegen, damit blockierte Provider schnelle Hotelquellen nicht verdrängen."
)
assert int(env_value("HOTEL_HEADLINE_TIMEOUT")) == 20
assert int(env_value("HOTEL_ENRICH_TIMEOUT")) == 35

assert _cacheable_component({"status": "manual_required"}) is False
assert _cacheable_component({"status": "partial"}) is False
assert _cacheable_component({"status": "ok", "hotel_options": [{"verified_total_price": 300}]}) is True

print("Hotel-Teilprovider bleiben innerhalb der äußeren Hotel-Zeitlimits isoliert: OK")
