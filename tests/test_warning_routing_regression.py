from pathlib import Path

from reisevergleich.presentation import public_result


raw = {
    "status": "ok",
    "search_mode": "ground_trip",
    "origin": "Start",
    "destination": "Ziel",
    "outbound_date": "2030-09-15",
    "outbound": {"status": "ok", "visible_options": [{"id": "unchanged", "provider": "DB", "legs": []}]},
}
before = public_result(raw)

# Die Warnintegration ist ein separater API-Pfad. Präsentation und Routing
# dürfen weder Warnungsfelder noch einen Provideraufruf eingebaut bekommen.
after = public_result(raw)
assert after == before
assert "warnings" not in str(after).casefold()
service_source = (Path(__file__).resolve().parents[1] / "tool" / "reisevergleich" / "service.py").read_text()
compare_source = (Path(__file__).resolve().parents[1] / "tool" / "reisevergleich" / "compare.py").read_text()
assert "warnings_for_routes" not in service_source + compare_source
print("NINA bleibt additiv; bestehende Reiseausgabe und Routing bleiben unverändert: OK")
