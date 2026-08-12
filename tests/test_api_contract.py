from reisevergleich.api import router
from reisevergleich.config import APP_VERSION
from reisevergleich.provider_cache import CACHE_GENERATION
from reisevergleich.models import TripRequest

ops = {route.operation_id for route in router.routes if getattr(route, "operation_id", None)}
assert "search_trip" in ops
assert all("reise_assistent" not in str(x).casefold() for x in ops)
fields = set(TripRequest.model_fields)
for required in {"origin","destination","departure_date","deutschlandticket","deutschlandticket_only","duration_value","duration_unit","return_date","hotel_min_stars"}:
    assert required in fields
assert CACHE_GENERATION == APP_VERSION
assert bytes.fromhex("726571756573745f74657874").decode() not in fields
print("Strukturierter API-Vertrag: OK")
