from reisevergleich.airports import resolve_destination_airport, resolve_origin_airports, resolve_feeder_airport_station, airport_identity_matches

assert resolve_origin_airports("Berlin Hbf", [])[0] == ["BER"]
assert resolve_destination_airport("Barcelona", None)[0] == "BCN"
assert resolve_feeder_airport_station("BER", None)[0] == "Flughafen BER - Terminal 1-2"
assert resolve_feeder_airport_station("AMS", None)[0] == "Schiphol Airport"
assert not airport_identity_matches("Flughafen JFK", "Flughafen Frankfurt")
assert not airport_identity_matches("Airport CDG", "Köln/Bonn Flughafen")
assert resolve_origin_airports("Leipzig Hbf", [])[0] == ["LEJ"]
print("Deterministische Flughafenauflösung: OK")

# trvl stellt im Image eine deterministische Flughafenliste bereit. Der Parser
# arbeitet ohne Netzwerkzugriff.
import tempfile
from pathlib import Path
import reisevergleich.airports as airports
with tempfile.TemporaryDirectory() as td:
    f=Path(td)/"airports.go"
    f.write_text('''var AirportNames = map[string]string{\n"FCO": "Rome Fiumicino",\n"LIS": "Lisbon",\n"LHR": "London Heathrow",\n"LGW": "London Gatwick",\n}\nvar airportSearchCities = map[string]string{\n"FCO": "Rome",\n"LHR": "London",\n"LGW": "London",\n}\n''', encoding='utf-8')
    old=airports.TRVL_AIRPORT_SOURCE
    airports.TRVL_AIRPORT_SOURCE=f
    airports._trvl_city_airports.cache_clear()
    try:
        assert airports.resolve_destination_airport("Rom", None)[0] == "FCO"
        assert airports.resolve_destination_airport("Lissabon", None)[0] == "LIS"
        assert airports.resolve_destination_airport("London", None)[0] == "LHR"
    finally:
        airports.TRVL_AIRPORT_SOURCE=old
        airports._trvl_city_airports.cache_clear()
print("Lokales trvl-Flughafenverzeichnis: OK")
