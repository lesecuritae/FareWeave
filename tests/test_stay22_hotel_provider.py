from pathlib import Path
import os
from reisevergleich.hotel_stay22 import parse_stay22_options
from reisevergleich.trvl import _select_hotel_options
from reisevergleich.models import HotelRequest

request = HotelRequest(
    location="Barcelona",
    checkin_date="2030-09-15",
    checkout_date="2030-09-22",
    adults=1,
    min_stars=3,
    property_type="hotel",
    max_results=3,
)
payload = {
    "meta": {
        "currency": "EUR",
        "checkin": "2030-09-15",
        "checkout": "2030-09-22",
        "nights": 7,
    },
    "results": [{
        "name": "Hotel Example",
        "type": "Accommodation",
        "url": "https://stay22.example/property",
        "location": {"address": "Barcelona, Spain"},
        "rating": {"value": 8.4, "hotelStars": None, "count": 120},
        "suppliers": {
            "booking": {"link": "https://booking.example", "price": {"total": 500}},
            "expedia": {"link": "https://expedia.example", "price": {"total": 640}},
            "hotelscom": {"link": "https://hotels.example", "price": {"total": 620}},
        },
    }],
}
options = parse_stay22_options(payload, request)
assert len(options) == 1
assert options[0]["verified_total_price"] == 620
assert options[0]["provider"] == "stay22:hotelscom"
assert options[0]["booking_url"] == "https://hotels.example"
assert options[0]["provider_min_stars"] == 3
assert "booking.example" not in options[0]["booking_url"]

wrong_dates = {**payload, "meta": {**payload["meta"], "checkout": "2030-09-23"}}
assert parse_stay22_options(wrong_dates, request) == []

trvl_options = [{"name": f"Hotel {index}", "verified_total_price": 500 + index} for index in range(3)]
stay22_option = {"name": "Independent Hotel", "verified_total_price": 700, "provider": "stay22:expedia"}
selected = _select_hotel_options(trvl_options, [stay22_option], 3)
assert len(selected) == 3
assert any(item.get("provider") == "stay22:expedia" for item in selected)

root = Path(os.environ.get("SOURCE_ROOT", Path(__file__).resolve().parents[1]))
provider_cache = (root / "tool/reisevergleich/provider_cache.py").read_text()
service = (root / "tool/reisevergleich/service.py").read_text()
assert 'return await raw_trvl.hotel_search(request)' in provider_cache
assert 'not request.include_hotel' in service

print("Stay22-Hotelprovider: Gesamtpreis, Zeitraum und Booking-Ausschluss OK")
