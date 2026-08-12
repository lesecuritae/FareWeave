from reisevergleich.feeder_db import _requires_separate_ticket


regional = {
    "legs": [{"product": "regional", "line": "FEX", "mode": "train"}],
}
long_distance = {
    "legs": [{"product": "nationalExpress", "line": "ICE 100", "mode": "train"}],
}

assert _requires_separate_ticket(regional) is False
assert _requires_separate_ticket(long_distance) is True
private_airport_bus = {"legs": [{"product": "bus", "line": "Bus LH-Ex", "mode": "bus"}]}
assert _requires_separate_ticket(private_airport_bus) is True
print("D-Ticket-Mischkette berechnet nur nicht abgedeckte Abschnitte: OK")
