from pathlib import Path

from reisevergleich.api import router
from reisevergleich.config import APP_VERSION
from reisevergleich.provider_cache import CACHE_GENERATION
from reisevergleich.models import TripRequest

ops = {route.operation_id for route in router.routes if getattr(route, "operation_id", None)}
assert "search_trip" in ops
coverage_routes = [route for route in router.routes if getattr(route, "path", None) == "/api/coverage"]
assert len(coverage_routes) == 1
assert coverage_routes[0].methods == {"POST"}
assert all("reise_assistent" not in str(x).casefold() for x in ops)
fields = set(TripRequest.model_fields)
for required in {"origin","destination","departure_date","deutschlandticket","deutschlandticket_only","duration_value","duration_unit","return_date","hotel_min_stars"}:
    assert required in fields
assert CACHE_GENERATION == APP_VERSION
assert bytes.fromhex("726571756573745f74657874").decode() not in fields
print("Strukturierter API-Vertrag: OK")

source = (Path(__file__).resolve().parents[1] / "tool" / "app.py").read_text(encoding="utf-8")
for header in (
    "Content-Security-Policy", "X-Content-Type-Options", "X-Frame-Options",
    "Referrer-Policy", "Permissions-Policy", "Cross-Origin-Opener-Policy",
):
    assert header in source
assert "frame-ancestors 'none'" in source
assert "object-src 'none'" in source
assert "lifespan=lifespan" in source
assert "start_scheduler()" in source and "await stop_scheduler(scheduler)" in source
assert 'app.mount("/assets", StaticFiles(directory=UI), name="assets")' in source
