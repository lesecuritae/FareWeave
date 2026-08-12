from reisevergleich.models import HotelRequest
from reisevergleich.trvl import _hotel_option_matches, _normalize_property_types

req = HotelRequest(location="Zielstadt", checkin_date="2030-09-16", checkout_date="2030-09-23")
assert req.property_type == "hotel" and req.min_stars == 3
assert _hotel_option_matches({"name":"Hotel Centro", "stars":3}, 3, "hotel")
assert not _hotel_option_matches({
    "name": "Room Lisboa",
    "stars": 3,
    "property_type": "hotel",
    "booking_url": "https://www.agoda.com/bluesock-hostels-lisboa/hotel/lisbon-pt.html",
}, 3, "hotel")
assert not _hotel_option_matches({"name":"Inout Hostel", "stars":3, "property_type":"hostel"}, 3, "hotel")
assert _hotel_option_matches({"name":"Inout Hostel", "stars":0, "property_type":"hostel"}, 0, "hostel")
normalized = _normalize_property_types([{"name": "Inout Hostel", "property_type": "hotel"}], "hostel")
assert normalized[0]["property_type"] == "hostel"
print("Hotelstandard ab 3 Sternen: OK")
