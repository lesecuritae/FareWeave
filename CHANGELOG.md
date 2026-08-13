# Changelog

## 0.0.2 - 2026-08-14

- Das Standard-Ergebnisbudget wurde auf zehn Verbindungen erweitert.
- Bei aktivierter Suche werden bis zu zwei tatsächlich verfügbare FlixTrain- und zwei FlixBus-Verbindungen berücksichtigt; die übrigen Plätze werden bevorzugt mit Bahnverbindungen gefüllt.
- FlixTrain und FlixBus werden getrennt klassifiziert und können einander nicht mehr durch die Reihenfolge der Providerantwort aus dem Ergebnisfenster verdrängen.
- FareWeave wertet den gesamten von trvl gelieferten Flix-Rohpool aus, bevor Zeitfenster, Flags, Deduplizierung, Ranking und sichtbare Auswahl angewendet werden.
- Konkrete Flix-Haltestellen werden über `station_id` aus aktuellen Flix-Daten aufgelöst und mit Name, Stadt, Adresse und Koordinaten erhalten.
- Die Oberfläche unterstützt eine automatische sowie eine verbindliche manuelle Auswahl konkret verfügbarer Flix-Halte.
- Generische Access-/Egress-Verbindungen verbinden den angefragten Bahnhof mit abweichenden tatsächlichen Flix-Halten; konkrete Halte und einzelne Segmente bleiben sichtbar.
- `departure_after`, ein Flix-Transferpuffer von 30 Minuten, Gesamtdauer und Kosten gelten für die vollständige Reisekette. Der Flughafenpuffer bleibt davon unabhängig bei standardmäßig 120 Minuten.
- Deutschlandticket-Zubringer werden nur bei tatsächlicher Abdeckung mit 0 EUR Zusatzkosten angesetzt. Unbekannte oder nicht belegte Zubringerpreise werden nicht als kostenlos ausgegeben.
- Unaufgelöste oder falsch zugeordnete Provider-Endpunkte und unplausible Fernumwege werden verworfen.
- Regressionstests für Flix-Auswahl, Haltestellenrouting, manuelle Stationswahl, Access/Egress, Zeitfenster und Ergebnisbudgets wurden erweitert.

## 0.0.1

- Erste öffentliche Version von FareWeave.
