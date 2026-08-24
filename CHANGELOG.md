# Changelog
## 0.0.6 - 2026-08-24

- Die nicht mehr nutzbare externe Unterkunftsschnittstelle wurde vollständig aus Laufzeitcode, Merge-Logik, Oberfläche, Docker-Konfiguration, Beispielumgebung, Dokumentation und Tests entfernt.
- Hotels laufen weiterhin über den isolierten trvl-Hotelpfad mit verifizierten Gesamtpreisen, schnellem Headline-Fallback und manuellem Google-Hotels-Gegencheck.

## 0.0.5 - 2026-08-24

- PR #5 wurde im vollständigen Planner-Pfad mit `max_results` 10, 24 und 48 validiert; Hotelanfragen bleiben auf das gültige Maximum 10 begrenzt und verursachen keine Pydantic-/HTTP-500-Fehler.
- PR #6 wurde gegen den echten Flix-GTFS-Feed validiert: München/Munich, Köln/Cologne und Wien/Vienna lösen dieselben korrekten Haltestellen auf.
- Frische GTFS-Daten werden lock-frei gelesen, während Refreshes weiterhin serialisiert und atomar installiert werden; parallele Suchen warten nicht mehr hinter einem unnötigen Feed-Lock.
- Die rein additive Bahn-Historienanreicherung besitzt ein hartes Gesamtbudget und einen isolierten Threadpool. Langsame oder abgebrochene Historien-Downloads blockieren weder GTFS/Cache/DB noch nachfolgende Suchen.
- Vier parallele reale Bodenreisen liefen in 22–31 Sekunden; unmittelbar folgende Suchen liefen in 21–23 Sekunden statt zuvor bis zu 131 Sekunden im gleichen Container.
- FlixBus-/FlixTrain-Zeiten, Livepreise und HTTPS-Direktlinks sowie DB-Verbindungen wurden in den Strecken München, Köln und Wien nach Berlin geprüft.
- Flug ohne Hotel und Flug mit realer Hotelanreicherung (`max_results=24`) liefen mit HTTP 200; ein fehlerhafter externer Hotelprovider blieb auf die Unterkunftssuche begrenzt.
- `curl_cffi` wurde von 0.16.0 auf 0.16.1 aktualisiert. Die direkten `db-vendo-client`-Abhängigkeiten `qs` und `uuid` werden im Image sicherheitsbedingt auf 6.15.3 bzw. 11.1.1 angehoben.
- TRVL `v1.21.4` wurde als weiterhin neuestes offizielles Release bestätigt und inklusive CLI-Verträge erneut gebaut und geprüft.

## 0.0.4 - 2026-08-21

- FlixBus- und FlixTrain-Fahrpläne werden aus dem strukturierten europäischen Transitous-GTFS mit vollständiger `calendar.txt`-/`calendar_dates.txt`-Auswertung gelesen.
- GTFS-Zeiten über 24 Uhr, Europe/Berlin-Ausgabe, Nachtfahrten, allgemeines Haltestellenmatching und strukturierte Agency-/Route-Type-Klassifikation sind abgedeckt.
- Feed-Updates erfolgen täglich mit bedingtem Download, vollständiger Validierung und atomarem Datenbanktausch; bei Updatefehlern bleibt der letzte gültige Feed aktiv.
- GTFS-Verbindungen erfinden keine Preise und werden nie als Deutschlandticket-abgedeckt markiert.
- Echte Preise aus der Flix-Such-API werden nur bei einer eindeutigen Übereinstimmung von Verkehrsmittel, Abfahrt und Ankunft an eine GTFS-Fahrt angefügt; sonst bleibt der Preis offen.
- Das starre 10er-Limit wurde durch standardmäßig 24 und maximal 48 Verbindungen ersetzt; die sichtbare Liste ist chronologisch.
- Kalender, mobile Karten und nicht-sticky Mobile-Navigation wurden überarbeitet.
- Ein requestisolierter Live-Loader zeigt echte Zustände von DB, Transitous, GTFS, FlixBus, FlixTrain und Ergebnisaufbereitung.
- Eine getrennte atomare History-Snapshot-Schicht kann tägliche, JSON-sichere Beobachtungen 30 Tage halten; beschädigte Daten werden verworfen und secret-verdächtige Felder abgelehnt.
- Ein fehlertoleranter Lifespan-Scheduler archiviert bereits berechnete History-Statistiken standardmäßig einmal täglich außerhalb von Nutzeranfragen und kann vollständig deaktiviert werden.
- Die Testumgebung ist als installierbares Python-Projekt mit separaten pytest-Abhängigkeiten reproduzierbar.

## 0.0.3 - 2026-08-14

- Direkte Docker-/Compose-Installationen benötigen keinen manuell gesetzten `DB_CFFI_TOKEN` mehr.
- Der interne Bridge-Token wird kryptographisch sicher erzeugt und im privaten Docker-Volume `fareweave-secrets` persistent gespeichert.
- Bestehende explizite `DB_CFFI_TOKEN`-Konfigurationen bleiben kompatibel und haben Vorrang.
- `curl_cffi` bleibt vollständig im App-Image enthalten.


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
