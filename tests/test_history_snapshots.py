from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta
from pathlib import Path

import reisevergleich.history_cache as history_cache


def configure_snapshot_store(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(history_cache, "HISTORY_CACHE_DIR", str(tmp_path / "history"))
    monkeypatch.setattr(history_cache, "HISTORY_SNAPSHOT_RETENTION_DAYS", 30)


def test_snapshot_save_and_load(monkeypatch, tmp_path: Path) -> None:
    configure_snapshot_store(monkeypatch, tmp_path)
    observed = datetime.fromisoformat("2026-08-21T12:00:00+02:00")
    target = history_cache.save_daily_snapshot("ICE:618:8000261:8000150", {"delay_minutes": 7}, observed_at=observed)
    assert target.is_file() and target.stat().st_mode & 0o077 == 0
    snapshots = history_cache.load_daily_snapshots("ICE:618:8000261:8000150", today=observed.date())
    assert len(snapshots) == 1
    assert snapshots[0]["snapshot_date"] == "2026-08-21"
    assert snapshots[0]["payload"] == {"delay_minutes": 7}


def test_snapshot_retention_30_days(monkeypatch, tmp_path: Path) -> None:
    configure_snapshot_store(monkeypatch, tmp_path)
    today = date(2026, 8, 21)
    for age in (0, 29, 30, 45):
        observed = datetime.combine(today - timedelta(days=age), datetime.min.time(), tzinfo=history_cache.TZ)
        history_cache.save_daily_snapshot("retention", {"age": age}, observed_at=observed)
    removed = history_cache.prune_daily_snapshots(today=today)
    snapshots = history_cache.load_daily_snapshots("retention", today=today)
    assert removed == 2
    assert [item["payload"]["age"] for item in snapshots] == [29, 0]


def test_snapshot_parallel_writes_are_atomic(monkeypatch, tmp_path: Path) -> None:
    configure_snapshot_store(monkeypatch, tmp_path)
    observed = datetime.fromisoformat("2026-08-21T12:00:00+02:00")
    with ThreadPoolExecutor(max_workers=12) as executor:
        list(executor.map(lambda value: history_cache.save_daily_snapshot("parallel", {"value": value}, observed_at=observed), range(48)))
    snapshots = history_cache.load_daily_snapshots("parallel", today=observed.date())
    assert len(snapshots) == 1
    assert snapshots[0]["payload"]["value"] in range(48)
    assert not list((tmp_path / "history").rglob("*.tmp"))


def test_corrupt_snapshot_is_ignored_and_removed(monkeypatch, tmp_path: Path) -> None:
    configure_snapshot_store(monkeypatch, tmp_path)
    observed = datetime.fromisoformat("2026-08-21T12:00:00+02:00")
    target = history_cache.save_daily_snapshot("corrupt", {"ok": True}, observed_at=observed)
    target.write_bytes(b"{broken")
    assert history_cache.load_daily_snapshots("corrupt", today=observed.date()) == []
    assert not target.exists()


def test_snapshot_rejects_secrets(monkeypatch, tmp_path: Path) -> None:
    configure_snapshot_store(monkeypatch, tmp_path)
    for payload in ({"token": "value"}, {"headers": {"authorization": "value"}}, {"api_key": "value"}):
        try:
            history_cache.save_daily_snapshot("secret-check", payload)
            raise AssertionError("secret-like snapshot field should be rejected")
        except ValueError:
            pass
