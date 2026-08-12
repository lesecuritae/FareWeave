# Drittanbieter

FareWeave lädt die beiden großen Transportbibliotheken beim Container-Build aus ihren jeweiligen Upstream-Repositories. Die folgenden Lizenzbedingungen gelten unabhängig von der FareWeave-Projektlizenz.

## trvl

- Projekt: [MikkoParkkola/trvl](https://github.com/MikkoParkkola/trvl)
- Build-Pin: Tag `v1.21.3`
- Lizenz: **PolyForm Noncommercial License 1.0.0** (<https://polyformproject.org/licenses/noncommercial/1.0.0/>)
- Required Notice: `Copyright (c) 2026 Mikko Parkkola (https://github.com/MikkoParkkola/trvl)`
- Die Lizenz erlaubt nur die dort definierten nichtkommerziellen Zwecke. Für kommerzielle Nutzung ist eine separate Lizenz des trvl-Rechteinhabers erforderlich.
- Die Originallizenz wird beim Container-Build nach `/usr/share/licenses/trvl/LICENSE` kopiert.

## db-vendo-client

- Projekt: [public-transport/db-vendo-client](https://github.com/public-transport/db-vendo-client)
- Build-Pin: Commit `5afe12a80e02cf111f38f3fa30ae87aaa532d1d6`
- Lizenz: **ISC License**
- Die Originallizenz wird beim Container-Build nach `/usr/share/licenses/db-vendo-client/LICENSE.md` kopiert.

## Weitere verwendete Projekte und Dienste

[Transitous](https://github.com/public-transport/transitous) wird als externe Routingquelle für öffentlichen Verkehr und Transfers verwendet. [BetterBahn](https://github.com/BetterBahn/betterbahn) wird in der README als ursprüngliche Motivation für das integrierte Split-Ticketing genannt; FareWeave übernimmt keinen BetterBahn-Code. Stay22 wird als externer Unterkunftsdienst eingebunden und ist keine mitgelieferte Open-Source-Bibliothek dieses Repositories.

## Direkte Python-Abhängigkeiten

Die direkt in `tool/requirements.txt` deklarierten Python-Pakete behalten ihre jeweiligen Upstream-Lizenzen. Dazu gehören FastAPI, HTTPX, Pydantic, Uvicorn und `curl_cffi`. Die tatsächlich installierten Versionen ergeben sich aus den dort definierten Versionsgrenzen; `curl_cffi` ist auf `0.16.0` gepinnt.

Diese Datei ist eine Übersicht und ersetzt keine Originallizenz. Beim Verteilen gebauter Images müssen die darin enthaltenen Drittanbieter-Lizenzdateien und Hinweise erhalten bleiben.
