from reisevergleich.trvl import compact_flight_options, flight_chronology_issues

valid = {
    "outbound": {"departure":"2030-09-15T13:45:00", "arrival":"2030-09-15T16:05:00"},
    "return": {"departure":"2030-09-22T18:00:00", "arrival":"2030-09-22T20:20:00"},
}
assert flight_chronology_issues(valid, "2030-09-22") == []
invalid = {
    "outbound": {"departure":"2030-09-15T13:45:00", "arrival":"2030-09-16T01:05:00"},
    "return": {"departure":"2030-09-15T22:45:00", "arrival":"2030-09-16T00:15:00"},
}
issues = flight_chronology_issues(invalid, "2030-09-23")
assert "return_date_mismatch" in issues
assert "return_not_after_outbound_arrival" in issues
collapsed = compact_flight_options({"flights": [{
    "price": 166, "currency": "USD", "provider": "skiplagged",
    "warnings": ["standard", "multi-stop"],
    "legs": [
        {"direction": "outbound", "origin": "AAA", "destination": "BBB", "departure": "2030-09-15T18:10+02:00", "arrival": "2030-09-16T01:05+02:00"},
        {"direction": "inbound", "origin": "BBB", "destination": "AAA", "departure": "2030-09-23T06:30+02:00", "arrival": "2030-09-24T08:00+02:00"},
    ],
}]}, "AAA", "BBB", 3)[0]
assert collapsed["outbound"]["stops"] == 1, collapsed
assert collapsed["return"]["stops"] == 1, collapsed

impossible_nonstop = {
    "outbound": {"departure":"2030-11-17T17:35+01:00", "arrival":"2030-11-17T18:50+01:00", "stops":0},
    "return": {"departure":"2030-11-22T07:45+01:00", "arrival":"2030-11-23T12:40+01:00", "stops":0},
}
assert "return_nonstop_duration_implausible" in flight_chronology_issues(impossible_nonstop, "2030-11-22")
print("Harte Flugchronologie: OK")
