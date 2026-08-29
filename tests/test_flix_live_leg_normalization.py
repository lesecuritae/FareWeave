from __future__ import annotations

import asyncio
import sqlite3
import tempfile
from pathlib import Path

from reisevergleich import gtfs_flix


HALLE_ID = "68c5db74-0034-41b2-b3ae-6947c837f77b"
BERLIN_ID = "394a5408-d778-4959-a63e-973253443ed2"


def _stop(station: str, time: str) -> dict:
    return {"station": station, "time": time}


async def regression() -> None:
    with tempfile.TemporaryDirectory() as temporary:
        database = Path(temporary) / "flix.sqlite3"
        with sqlite3.connect(database) as db:
            db.execute(
                "CREATE TABLE stop(stop_id TEXT PRIMARY KEY, name TEXT, parent_station TEXT, "
                "timezone TEXT, latitude REAL, longitude REAL)"
            )
            db.executemany(
                "INSERT INTO stop VALUES(?,?,?,?,?,?)",
                [
                    (HALLE_ID, "Halle (Saale) Central Station (FlixTrain)", "", "Europe/Berlin", 51.477, 11.987),
                    (BERLIN_ID, "Berlin Central Station (FlixTrain)", "", "Europe/Berlin", 52.525, 13.369),
                ],
            )

        live = {
            "candidate_routes": [{
                "provider": "FlixTrain",
                "provider_code": "flix",
                "flix_kind": "train",
                "type": "train",
                "departure": _stop("Leipzig Central Station", "2026-08-30T12:04:00+02:00"),
                "arrival": _stop("Dortmund Central Station", "2026-08-30T20:36:00+02:00"),
                "legs": [
                    {"type": "train", "provider": "flixbus", "departure": _stop("Leipzig Central Station", "2026-08-30T12:04:00+02:00"), "arrival": _stop(HALLE_ID, "2026-08-30T12:27:00+02:00")},
                    {"type": "train", "provider": "flixbus", "departure": _stop(HALLE_ID, "2026-08-30T12:46:00+02:00"), "arrival": _stop(BERLIN_ID, "2026-08-30T14:00:00+02:00")},
                    {"type": "train", "provider": "flixbus", "departure": _stop(BERLIN_ID, "2026-08-30T16:39:00+02:00"), "arrival": _stop("Dortmund Central Station", "2026-08-30T20:36:00+02:00")},
                ],
            }],
            "provider_status": {"ok": True},
        }

        normalized = await gtfs_flix.normalize_live_routes(live, database=database)
        route = normalized["candidate_routes"][0]
        assert len(route["legs"]) == 3
        assert {leg["provider"] for leg in route["legs"]} == {"FlixTrain"}
        assert {leg["mode"] for leg in route["legs"]} == {"train"}
        assert route["legs"][0]["arrival"]["station"] == "Halle (Saale) Central Station (FlixTrain)"
        assert route["legs"][0]["arrival"]["station_id"] == HALLE_ID
        assert route["legs"][1]["arrival"]["station"] == "Berlin Central Station (FlixTrain)"
        assert route["legs"][1]["arrival"]["station_id"] == BERLIN_ID

        # A direct one-leg FlixTrain must retain one complete leg; it must not
        # be mistaken for a missing partial-route structure.
        direct = {"candidate_routes": [{
            **live["candidate_routes"][0],
            "legs": [live["candidate_routes"][0]["legs"][0]],
        }]}
        direct_normalized = await gtfs_flix.normalize_live_routes(direct, database=database)
        assert len(direct_normalized["candidate_routes"][0]["legs"]) == 1


asyncio.run(regression())
print("Flix-Live-Legs und GTFS-Haltepunkte werden konsistent normalisiert: OK")
