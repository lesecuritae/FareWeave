from reisevergleich.presentation import _flight, _hotel, _trip_context


flight = _flight(
    {
        "provider": "Provider A",
        "price": 120,
        "currency": "EUR",
        "outbound": {"departure_airport": "AAA", "arrival_airport": "BBB"},
    },
    manual_url="https://example.test/flights",
)
assert flight["manual_url"] == "https://example.test/flights"

hotel = _hotel(
    {
        "status": "manual_required",
        "hotel_options": [],
        "manual_booking_url": "https://example.test/hotels",
    },
    "2030-08-19",
    "2030-08-22",
)
assert hotel["manual_url"] == "https://example.test/hotels"

context = _trip_context({
    "search_mode": "trip_plan",
    "trip_chain": ["outbound_flight", "return_flight"],
    "departure_date": "2030-08-19",
    "return_date": "2030-08-22",
    "destination_iata": "BBB",
    "destination_city": "Beta",
    "recommended_origin_airport": "AAA",
    "airport_candidates": [{
        "origin_airport": "AAA",
        "selected_flight": {
            "provider": "Provider A",
            "outbound": {"departure_airport": "AAA", "arrival_airport": "BBB"},
            "return": {"departure_airport": "BBB", "arrival_airport": "AAA"},
        },
        "flight_manual_url": "https://example.test/flights",
    }],
})
assert context["flight"]["manual_url"] == "https://example.test/flights"

print("Buchungs- und Suchlinks bleiben öffentlich verfügbar: OK")
