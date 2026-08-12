from reisevergleich.feeder_common import _feeder_option_score, diverse_feeder_options

options = [
    {"type":"deutschlandticket_direct", "requires_deutschlandticket":True, "price_known":True, "total_price":0.0, "duration_minutes":125, "departure":"2030-09-15T06:00", "arrival":"2030-09-15T08:05"},
    {"type":"deutschlandticket_plus_db", "requires_deutschlandticket":True, "price_known":True, "total_price":9.99, "duration_minutes":55, "departure":"2030-09-15T06:30", "arrival":"2030-09-15T07:25"},
    {"type":"s_bahn_plus_flixtrain", "requires_deutschlandticket":False, "price_known":True, "total_price":6.99, "duration_minutes":68, "departure":"2030-09-15T06:10", "arrival":"2030-09-15T07:18"},
    {"type":"re_plus_ice", "requires_deutschlandticket":False, "price_known":True, "total_price":12.99, "duration_minutes":40, "departure":"2030-09-15T06:20", "arrival":"2030-09-15T07:00"},
]
ranked = diverse_feeder_options(options, "dticket_first", limit=8)
assert ranked[0]["requires_deutschlandticket"] is True
assert any(x["type"] == "s_bahn_plus_flixtrain" for x in ranked), ranked
assert any(x["type"] == "re_plus_ice" for x in ranked), ranked
cheapest = min(ranked, key=lambda x: _feeder_option_score(x, "cheapest"))
fastest = min(ranked, key=lambda x: _feeder_option_score(x, "fastest"))
assert cheapest["type"] == "deutschlandticket_direct"
assert fastest["type"] == "re_plus_ice"
print("D-Ticket-Priorität mit günstigen/schnellen Alternativen: OK")
