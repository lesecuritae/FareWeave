from reisevergleich.presentation import public_result


raw = {
    "status": "ok",
    "search_mode": "trip_plan",
    "departure_date": "2030-12-01",
    "return_date": "2030-12-05",
    "requested_stay_nights": 4,
    "recommended_origin_airport": "FRA",
    "destination_iata": "BCN",
    "destination_city": "Zielstadt",
    "airport_candidates": [{
        "origin_airport": "FRA",
        "feeder_direct_query": {"origin": "Frankfurt (Main) Hbf"},
        "selected_flight": {
            "provider": "test",
            "price": 100,
            "currency": "EUR",
            "outbound": {
                "departure_airport": "FRA", "arrival_airport": "BCN",
                "departure": "2030-12-01T10:00+01:00", "arrival": "2030-12-01T12:00+01:00",
            },
            "return": {
                "departure_airport": "BCN", "arrival_airport": "FRA",
                "departure": "2030-12-05T13:00+01:00", "arrival": "2030-12-05T15:00+01:00",
            },
        },
        "outbound_destination_transfer": {
            "status": "ok", "date": "2030-12-01", "depart_after": "12:00",
            "options": [{
                "provider": "Transitous", "type": "public_transport",
                "origin": "Beispielflughafen XYZ", "destination": "Zentralbahnhof",
                "departure": "2030-12-01T12:15:00+01:00", "arrival": "2030-12-01T12:50:00+01:00",
                "duration_minutes": 35, "price": 0, "currency": "EUR",
                "price_note": "Transitous liefert keinen belastbaren DB-Ticketpreis.",
            }],
        },
        "return_destination_transfer": {
            "status": "ok", "date": "2030-12-05", "arrive_before": "11:00",
            "options": [{
                "provider": "Transitous", "type": "public_transport",
                "origin": "Zentralbahnhof", "destination": "Beispielflughafen XYZ",
                "departure": "2030-12-05T09:30:00+01:00", "arrival": "2030-12-05T10:15:00+01:00",
                "duration_minutes": 45, "price": 0, "currency": "EUR",
                "price_note": "Transitous liefert keinen belastbaren DB-Ticketpreis.",
            }],
        },
    }],
}

ctx = public_result(raw)["response_context"]
outbound = ctx["outbound_transfer"]["options"][0]
returned = ctx["return_transfer"]["options"][0]

assert outbound["departure"] == "2030-12-01T12:15:00+01:00", outbound
assert outbound["arrival"] == "2030-12-01T12:50:00+01:00", outbound
assert outbound["departure_station"] == "Beispielflughafen XYZ", outbound
assert outbound["arrival_station"] == "Zentralbahnhof", outbound
assert returned["departure"] == "2030-12-05T09:30:00+01:00", returned
assert returned["arrival"] == "2030-12-05T10:15:00+01:00", returned
assert "price" not in outbound and "currency" not in outbound, outbound
assert "price" not in returned and "currency" not in returned, returned
print("Transferdarstellung behält Zeiten und erfindet keinen Nulltarif: OK")
