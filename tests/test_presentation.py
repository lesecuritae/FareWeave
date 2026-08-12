from reisevergleich.presentation import public_result

flight = {
    "price": 140.52, "currency":"EUR", "provider":"test",
    "outbound": {"departure_airport":"AAA", "arrival_airport":"BBB", "departure":"2030-09-15T13:45", "arrival":"2030-09-15T16:05", "stops":0},
    "return": {"departure_airport":"BBB", "arrival_airport":"AAA", "departure":"2030-09-22T18:00", "arrival":"2030-09-22T20:20", "stops":0},
}
dticket = {"type":"deutschlandticket_direct","requires_deutschlandticket":True,"price_known":True,"total_price":0.0,"duration_minutes":50,"departure":"2030-09-15T10:00","arrival":"2030-09-15T10:50","segments":[]}
paid = {"type":"re_plus_ice","requires_deutschlandticket":False,"price_known":True,"total_price":9.99,"duration_minutes":35,"departure":"2030-09-15T10:10","arrival":"2030-09-15T10:45","segments":[]}
raw = {
  "status":"ok", "search_mode":"trip_plan", "departure_date":"2030-09-15", "return_date":"2030-09-22", "requested_stay_nights":7,
  "recommended_origin_airport":"AAA", "destination_iata":"BBB", "destination_city":"Zielstadt", "airport_buffer_minutes":120, "return_airport_buffer_minutes":60,
  "airport_candidates":[{
      "origin_airport":"AAA", "feeder_direct_query":{"origin":"Berlin Hbf"},
      "selected_flight": {}, "flight_options":[flight],
      "outbound_feeder":{"status":"ok","airport_station":"Flughafen BER - Terminal 1-2","selected_option":dticket,"alternatives":[paid]},
  }]
}
out = public_result(raw)
ctx = out["response_context"]
assert ctx["flight"]["outbound"]["from"] == "AAA"
assert ctx["flight"]["return"]["from"] == "BBB"
assert ctx["outbound_feeder"]["views"]["deutschlandticket"]["requires_deutschlandticket"] is True
assert ctx["outbound_feeder"]["views"]["fastest"]["type"] == "re_plus_ice"
assert bytes.fromhex("726573706f6e73655f696e737472756374696f6e").decode() not in str(out)
print("Öffentliche UI-Daten und Flugfallback: OK")
