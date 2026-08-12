from reisevergleich.models import TripRequest

BASE = dict(origin="Startort", destination="Zielort", departure_date="2030-09-15")

assert TripRequest(**BASE, duration_value=8, duration_unit="days").stay_nights == 7
assert TripRequest(**BASE, duration_value=1, duration_unit="weeks").stay_nights == 7
assert TripRequest(**BASE, duration_value=2, duration_unit="weeks").stay_nights == 14
assert TripRequest(**BASE, duration_value=14, duration_unit="nights").stay_nights == 14

req = TripRequest(**BASE, deutschlandticket=True)
assert req.effective_feeder_preference == "dticket_first"
req = TripRequest(**BASE, deutschlandticket=False)
assert req.effective_feeder_preference == "cheapest"

only = TripRequest(**BASE, deutschlandticket=True, deutschlandticket_only=True)
assert only.deutschlandticket_only is True
try:
    TripRequest(**BASE, deutschlandticket=False, deutschlandticket_only=True)
except ValueError:
    pass
else:
    raise AssertionError("D-Ticket-only ohne vorhandenes D-Ticket muss abgewiesen werden")

hotel = TripRequest(**BASE)
assert hotel.hotel_property_type == "hotel"
assert hotel.hotel_min_stars == 3
hostel = TripRequest(**BASE, hotel_property_type="hostel")
assert hostel.hotel_min_stars == 0


without_hotel = TripRequest(
    **BASE,
    travel_mode="ground",
    include_hotel=False,
    hotel_property_type="none",
)
assert without_hotel.hotel_property_type == "none"

print("Strukturierte Eingabe und Dauerlogik: OK")
