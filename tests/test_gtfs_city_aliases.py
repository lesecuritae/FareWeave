"""Deutsche Städtenamen müssen die englisch benannten Flix-GTFS-Stops treffen.

Der Feed führt viele Städte nur unter dem englischen Namen. Ohne Angleichung liefert
eine Suche nach "München" keinen Stop, und der Vergleich zeigt still nur noch Bahn-
verbindungen — ein stiller Qualitätsverlust ohne Fehlermeldung.
"""

from reisevergleich.gtfs_flix import CITY_ALIASES, _key, _place_tokens, stop_score

MATCH_THRESHOLD = 60  # siehe _stop_suggestions_sync

# Echte Stop-Namen aus dem eu_flixbus-Feed.
cases = [
    ("München", "Munich central bus station"),
    ("Muenchen", "Munich central bus station"),
    ("München", "Munich International Airport"),
    ("Köln", "Cologne"),
    ("Koeln", "Cologne"),
    ("Nürnberg", "Nuremberg"),
    ("Hannover", "Hanover"),
    ("Wien", "Vienna"),
    ("Prag", "Prague"),
    ("Mailand", "Milan"),
    ("Brüssel", "Brussels"),
    ("Kopenhagen", "Copenhagen"),
]
for query, stop in cases:
    assert stop_score(query, stop) >= MATCH_THRESHOLD, (
        f"{query!r} findet {stop!r} nicht (score={stop_score(query, stop)})"
    )

# Die englische Eingabe darf dadurch nicht schlechter werden.
assert stop_score("Munich", "Munich central bus station") >= MATCH_THRESHOLD
assert stop_score("Vienna", "Vienna International Busterminal") >= MATCH_THRESHOLD

# Zürich braucht keinen Alias für die Umlautform: _key entfernt Diakritika und trifft
# den englischen Namen bereits. Nur die ASCII-Umschrift wird abgebildet.
assert _key("Zürich") == "zurich"
assert _key("Zuerich") == "zurich"

# Keine falschen Treffer: die Angleichung darf keine fremden Orte verbinden.
assert stop_score("München", "Berlin ZOB") == 0
assert stop_score("Köln", "Hamburg Airport") == 0
assert stop_score("Wien", "Warsaw") == 0

# Angleichung wirkt auf Token-Ebene, Zusätze bleiben erhalten.
assert _key("München Hbf") == "munich hbf"
assert _place_tokens("München Hbf") == {"munich"}

# Jeder Alias bildet auf einen anderen Token ab und ist selbst kein Ziel-Token
# (sonst würde eine zweite Anwendung das Ergebnis erneut verschieben).
for source, target in CITY_ALIASES.items():
    assert source != target, f"Alias {source!r} zeigt auf sich selbst"
    assert target not in CITY_ALIASES, f"Alias-Ziel {target!r} ist selbst ein Alias"
    assert _key(source) == target, f"_key({source!r}) ergibt nicht {target!r}"

print("Deutsche Städtenamen treffen die englischen Flix-GTFS-Stops: OK")
