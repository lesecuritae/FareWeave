from pathlib import Path
import os
root = Path(os.environ.get("SOURCE_ROOT", Path(__file__).resolve().parents[1])) / "tool" / "ui"
html = (root / "index.html").read_text(encoding="utf-8")
js = (root / "app.js").read_text(encoding="utf-8")
css = (root / "styles.css").read_text(encoding="utf-8")
assert "FareWeave" in html
assert bytes.fromhex("52656973656b6c6172").decode() not in html
for needle in [
    "Bahn &amp; Bus",
    "Reine Bodenreise",
    "Komplette Reise",
    "Bahn/Bus + Flug + Transfer + Unterkunft",
    "Flug &amp; Unterkunft",
    "Ohne Bahn-/Buszubringer",
    'data-mode="flight_stay"',
]:
    assert needle in html
for needle in ["Abreise", "Rückreise", "Deutschlandticket vorhanden?", 'data-dticket="true"', 'data-dticket="false"']:
    assert needle in html
for needle in [
    'aria-label="Unterkunftsart"',
    'data-hotel-type="hotel"',
    'data-hotel-type="hostel"',
    'data-hotel-type="apartment"',
    'data-hotel-type="none"',
    'id="dticketOnly"',
]:
    assert needle in html
for needle in ["deutschlandticket", "D-Ticket", "Günstigste", "Schnellste", "/api/search"]:
    assert needle in js
for needle in [
    "deutschlandticket_only:",
    "hotel_property_type: state.hotelType",
    "hotel_min_stars: hotelUsesStars",
    "function syncHotelType()",
    "timeZone: 'Europe/Berlin'",
    "function groundAlternativesHtml(",
    "function groundConnectionsHtml(",
    "function reliabilityHtml(",
    "Keine ausreichenden historischen Daten",
    "geringe Datenbasis",
    "Historische Details",
    "component?.connections",
    "connection-card",
    "Misch- & Split-Tickets",
    "include_feeder: state.travelMode === 'flight'",
    "travel_mode: state.travelMode === 'ground' ? 'ground' : 'flight'",
]:
    assert needle in js
assert "state.hotelType === 'hotel' || state.hotelType === 'resort'" in js
assert bytes.fromhex("726571756573745f74657874").decode() not in js
print("UI-Vertrag: OK")

assert "3 sinnvolle" not in html
assert "maxResults" not in html
assert "journey_type: state.journeyType" in js
assert "max_results: 3" in js

assert "class=\"lodging-panel hidden\"" in html
assert "classList.toggle(\"hidden\", isGround || state.journeyType === 'one_way')" in js
assert "classList.toggle(\"disabled\", isGround || state.journeyType === 'one_way')" not in js

assert html.count("</body>") == 1
assert html.count("flight-option") == 5
assert 'class="check flight-option"' in html
assert "querySelectorAll('.flight-option')" in js

assert html.count("feeder-option") == 4
assert "querySelectorAll('.feeder-option')" in js
assert "isGround && option.classList.contains('flight-option')" in js
assert "ticketPanel').classList.toggle('disabled'" not in js

assert "provider_min_stars" in js
assert "via Stay22" in js

for label in ["Angebot prüfen/buchen", "Weitere Angebote öffnen"]:
    assert label in js

for removed in ["Wie lange", 'id="durationValue"', 'id="durationUnit"', 'data-journey-type=', 'data-stay=', 'data-nights=', 'stay-tabs', 'night-presets']:
    assert removed not in html
assert 'Rückreise <small>(optional)</small>' in html
assert 'grid-template-areas:"departure time" "return one-way"' in css
for undersized in range(10, 16):
    assert f"font-size:{undersized}px" not in css
    assert f"font-size: {undersized}px" not in css
assert "function dateDifferenceInDays(start, end)" in js
assert "state.journeyType = returnDate ? 'round_trip' : 'one_way'" in js
assert "return_mode: 'date'" in js
assert "duration_value: state.durationNights" in js
assert "return_date: state.journeyType === 'round_trip' ? $('returnDate').value : null" in js
assert "$('returnDate').addEventListener('change', syncJourneyDates)" in js
assert 'id="oneWayButton"' in html
assert "$('oneWayButton').addEventListener('click'" in js
assert "$('returnDate').value = ''" in js

for credit in ["Entwickelt von lesecuritae", "Mit Vibe-Coding-Unterstützung", "Nutzt trvl für ausgewählte Providerabfragen", "https://github.com/MikkoParkkola/trvl"]:
    assert credit in html
assert 'class="project-credit"' in html
assert "justify-content:center" in css
assert "margin:20px auto 0" in css
assert "margin: -42px" not in css
assert "margin: -28px" not in css
assert "overflow-wrap:anywhere" in css
assert "calc((100vw - 1132px)/2)" in css
assert "width:min(calc(100% - 48px), 1132px)" in css
assert "min-height:44px" in css

assert "Komplett ohne KI: eigenständiger, deterministischer Reisevergleich mit Split-Ticketing" in html
assert "BetterBahn" not in html
