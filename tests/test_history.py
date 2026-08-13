from __future__ import annotations

import asyncio
from datetime import date, datetime

import reisevergleich.history as history
from reisevergleich.history import (
    build_relation_samples, calculate_statistics, derive_run_instance_id,
    normalize_eva, normalize_train_number, normalize_train_type, reliability_label,
)


def stop(run, station, eva, planned, changed, *, arrival=False, canceled=False):
    prefix = "arrival" if arrival else "departure"
    return {
        "id": f"{run}-{station}", "eva": eva, "train_line_station_num": station,
        "is_canceled": canceled, "time": planned,
        f"{prefix}_planned_time": planned, f"{prefix}_change_time": changed,
    }


assert derive_run_instance_id("-3889563661905709281-2406301936-13") == "-3889563661905709281-2406301936"
for invalid in (None, "", "ride-13", "-1-240630193-13", "-1-2406301936-x"):
    assert derive_run_instance_id(invalid) is None
assert normalize_eva("08000261") == normalize_eva("8000261") == "8000261"
assert normalize_eva("de:stop:001") == "de:stop:001"
assert normalize_train_type(" ICE \t") == "ICE"
assert normalize_train_number(" 001A ") == "001A"

rows = [
    stop("-10-2407010800", 1, "08000261", "2026-07-01T08:00:00", "2026-07-01T08:03:00"),
    stop("-10-2407010800", 4, "08000150", "2026-07-01T10:00:00", "2026-07-01T10:12:00", arrival=True),
    stop("-10-2407020800", 1, "08000261", "2026-07-02T08:00:00", "2026-07-02T07:58:00"),
    stop("-10-2407020800", 4, "08000150", "2026-07-02T10:00:00", "2026-07-02T10:04:00", arrival=True),
]
samples = build_relation_samples(rows, "8000261", "8000150")
assert len(samples) == 2
assert {sample["run_instance_id"] for sample in samples} == {"-10-2407010800", "-10-2407020800"}
assert samples[0]["departure_delay_minutes"] == 3
assert samples[0]["arrival_delay_minutes"] == 12
assert samples[1]["departure_delay_minutes"] == -2
assert build_relation_samples(rows, "8000150", "8000261") == []
assert build_relation_samples([rows[0]], "8000261", "8000150") == []
assert build_relation_samples([], "8000261", "8000150") == []

canceled_rows = [
    stop("-12-2407040800", 1, "8000261", "2026-07-04T08:00:00", "2026-07-04T08:30:00", canceled=True),
    stop("-12-2407040800", 4, "8000150", "2026-07-04T10:00:00", "2026-07-04T11:00:00", arrival=True),
]
canceled = build_relation_samples(canceled_rows, "8000261", "8000150")
assert canceled[0]["explicit_cancellation"] is True
assert canceled[0]["arrival_delay_minutes"] is None

night = [
    stop("-13-2407312350", 8, "8000261", "2026-07-31T23:50:00", "2026-07-31T23:55:00"),
    stop("-13-2407312350", 12, "8000150", "2026-08-01T03:10:00", "2026-08-01T03:20:00", arrival=True),
]
doubled = build_relation_samples(night + night, "8000261", "8000150")
assert len(doubled) == 1 and doubled[0]["service_date"] == date(2026, 7, 31)

stat_samples = []
for index, value in enumerate([0, 2, 4, 6, 8, 10, 12, 20, 30, 40], 1):
    stat_samples.append({
        "run_instance_id": str(index), "service_date": date(2026, 7, index),
        "planned_departure": datetime(2026, 7, index, 8), "explicit_cancellation": False,
        "departure_delay_minutes": value / 2, "arrival_delay_minutes": value,
    })
stat_samples.append({
    "run_instance_id": "cancel", "service_date": date(2026, 7, 11),
    "planned_departure": datetime(2026, 7, 11, 8), "explicit_cancellation": True,
    "departure_delay_minutes": None, "arrival_delay_minutes": None,
})
stats = calculate_statistics(stat_samples, 90)
assert stats["sample_count"] == 11 and stats["explicit_cancellations"] == 1
assert stats["cancellation_rate"] == round(1 / 11, 3)
assert stats["median_arrival_delay_minutes"] == 9
assert stats["p90_arrival_delay_minutes"] == 30 and stats["p95_arrival_delay_minutes"] == 40
assert stats["on_time_5_rate"] == .3 and stats["late_over_10_rate"] == .4
assert stats["direct_reliability_rate"] == round(6 / 11, 3)
assert calculate_statistics(stat_samples[:2], 90)["status"] == "insufficient_data"
assert reliability_label(93, "connection") == "Anschluss sehr wahrscheinlich"
assert reliability_label(82, "connection") == "Anschluss wahrscheinlich"
assert reliability_label(61, "connection") == "Anschluss unsicher"
assert reliability_label(43, "connection") == "Anschluss eher unwahrscheinlich"


async def integration_tests():
    base_stats = {
        "status": "ok", "sample_count": 10, "reliability_sample_count": 10,
        "quality": "limited", "direct_reliability_rate": .8,
        "explicit_cancellations": 1, "_arrival_delay_samples": [0, 1, 2, 3, 4, 5, 8, 12, 20],
    }
    direct = {
        "id": "db-1", "price": 39.99, "departure": "2030-10-10T09:00:00+02:00",
        "arrival": "2030-10-10T11:00:00+02:00", "duration_minutes": 120, "transfers": 0,
        "booking_url": "https://example.invalid", "legs": [{
            "line": "ICE 618", "train_number": "618", "train_type": "ICE", "mode": "train",
            "departure": "2030-10-10T09:00:00+02:00", "arrival": "2030-10-10T11:00:00+02:00",
            "origin": {"id": "08000261", "name": "München Hbf"},
            "destination": {"id": "08000150", "name": "Frankfurt Hbf"},
        }],
    }
    original_stats = history._statistics_for_leg

    async def fake_stats(*args, **kwargs):
        assert args[:4] == ("ICE", "618", "8000261", "8000150")
        return dict(base_stats)

    history._statistics_for_leg = fake_stats
    try:
        enriched = (await history.enrich_routes_history([direct]))[0]
    finally:
        history._statistics_for_leg = original_stats
    for key in ("id", "price", "departure", "arrival", "duration_minutes", "transfers", "booking_url"):
        assert enriched[key] == direct[key]
    assert enriched["reliability"]["percent"] == 80
    assert enriched["reliability"]["label"] == "Zuverlässigkeit hoch"
    assert "_arrival_delay_samples" not in enriched["legs"][0]["reliability"]
    assert "reliability" not in direct

    incoming = {**direct["legs"][0], "reliability": dict(base_stats), "arrival": "2030-10-10T11:00:00+02:00"}
    loose = {**direct["legs"][0], "departure": "2030-10-10T11:20:00+02:00"}
    tight = {**loose, "departure": "2030-10-10T11:05:00+02:00"}
    loose_value = history._connection(incoming, loose)
    tight_value = history._connection(incoming, tight)
    assert tight_value["percent"] < loose_value["percent"]
    assert tight_value["scheduled_transfer_minutes"] == 5
    assert loose_value["scheduled_transfer_minutes"] == 20

    async def broken(*_args, **_kwargs):
        raise RuntimeError("duckdb_unavailable")
    history._statistics_for_leg = broken
    try:
        unavailable = (await history.enrich_routes_history([direct]))[0]
    finally:
        history._statistics_for_leg = original_stats
    assert unavailable["id"] == direct["id"] and unavailable["price"] == direct["price"]
    assert unavailable["legs"][0]["reliability"]["reason"] == "duckdb_unavailable"

    old_enabled = history.HISTORY_ENABLED
    history.HISTORY_ENABLED = False
    try:
        assert await history.enrich_routes_history([direct]) == [direct]
    finally:
        history.HISTORY_ENABLED = old_enabled


asyncio.run(integration_tests())
print("History-Relationen, Statistiken, Wahrscheinlichkeiten und additives Enrichment: OK")
