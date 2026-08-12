from reisevergleich.ground_connections import complete_connections
from reisevergleich.presentation import _ground_trip_context


def route(name, departure, arrival, price, lines):
    legs = [
        {
            "line": line,
            "mode": "train",
            "origin": f"Station {index}",
            "destination": f"Station {index + 1}",
            "departure": f"2030-08-19T{6 + index:02d}:00+02:00",
            "arrival": f"2030-08-19T{6 + index:02d}:40+02:00",
        }
        for index, line in enumerate(lines)
    ]
    return {
        "id": name,
        "departure": departure,
        "arrival": arrival,
        "duration_minutes": 180,
        "transfers": len(legs) - 1,
        "price": price,
        "currency": "EUR",
        "legs": legs,
    }


first = route("first", "2030-08-19T06:00+02:00", "2030-08-19T09:00+02:00", 29.90, ["RE 1", "ICE 2", "S 3", "Bus 4"])
second = route("second", "2030-08-19T07:00+02:00", "2030-08-19T10:00+02:00", 39.90, ["RE 5", "ICE 6"])
third = route("third", "2030-08-19T08:00+02:00", "2030-08-19T11:00+02:00", 49.90, ["ICE 7"])

component = {
    "db_options": [first, second, third],
    "flix_options": [],
    "recommendation": {"cheapest_with_live_price": first, "fastest": first},
}
connections = complete_connections(component)
assert len(connections) == 3
assert len(connections[0]["legs"]) == 4
assert connections[0]["labels"] == ["Günstigste", "Schnellste"]
assert len([item for item in connections if item["id"] == "first"]) == 1
assert connections[1]["price"] == 39.90 and connections[1]["legs"][0]["line"] == "RE 5"

single = complete_connections({"db_options": [first], "recommendation": {"fastest": first}})
assert len(single) == 1

inbound = route("inbound", "2030-08-26T12:00+02:00", "2030-08-26T15:00+02:00", 35.90, ["ICE 8", "RE 9"])
context = _ground_trip_context({
    "route": {"origin": "Alpha", "destination": "Beta"},
    "outbound": component,
    "return": {"db_options": [inbound], "recommendation": {"cheapest_with_live_price": inbound}},
    "deutschlandticket": {"outbound": [], "return": []},
})
assert len(context["outbound"]["connections"]) == 3
assert len(context["return"]["connections"]) == 1
assert context["return"]["connections"][0]["id"] == "inbound"


structured_line = route("structured", "2030-08-19T09:00+02:00", "2030-08-19T12:00+02:00", 59.90, ["ICE 10"])
structured_line["legs"][0]["line"] = {"name": "ICE 10", "number": "10"}
structured_copy = {**structured_line, "id": "structured-copy", "legs": [{**structured_line["legs"][0], "line": {"number": "10", "name": "ICE 10"}}]}
structured_connections = complete_connections({"db_options": [structured_line, structured_copy], "recommendation": {}})
assert len(structured_connections) == 1

print("Vollständige Bodenverbindungen und Deduplizierung: OK")
