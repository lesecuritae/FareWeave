from __future__ import annotations

import asyncio
import hashlib
import os
import re
import tempfile
import threading
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from curl_cffi import requests as curl_requests

from . import cache
from .config import (
    HISTORY_CACHE_DIR, HISTORY_CACHE_MAX_GB, HISTORY_MAX_CONCURRENCY,
    HISTORY_REMOTE_TIMEOUT, HISTORY_SOURCE_REVISION,
)

SOURCE = "piebro/deutsche-bahn-data"
DETAIL_SCHEMA = 1
DETAIL_COLUMNS = (
    "id", "station_name", "xml_station_name", "eva", "train_number", "line_number",
    "final_destination_station", "time", "is_canceled", "train_type", "train_line_ride_id",
    "train_line_station_num", "arrival_planned_time", "arrival_change_time",
    "departure_planned_time", "departure_change_time",
)
_MONTH_RE = re.compile(r"^20\d{2}-(0[1-9]|1[0-2])$")
_locks: dict[str, asyncio.Lock] = {}
_active: set[str] = set()
_reading: set[str] = set()
_guard = threading.Lock()
_remote_fill_limiter = threading.BoundedSemaphore(max(1, HISTORY_MAX_CONCURRENCY))


@dataclass(frozen=True)
class DetailSpec:
    train_type: str
    train_number: str
    year: int
    month: int

    @property
    def month_id(self) -> str:
        return f"{self.year:04d}-{self.month:02d}"


def detail_cache_key(spec: DetailSpec) -> str:
    raw = f"{DETAIL_SCHEMA}\0{spec.train_type}\0{spec.train_number}\0{spec.month_id}"
    return hashlib.sha256(raw.encode()).hexdigest()


def _safe_segment(value: str) -> str:
    label = re.sub(r"[^A-Z0-9._-]+", "_", value.upper()).strip("._")
    if not label:
        raise ValueError("empty cache path segment")
    return f"{label[:48]}-{hashlib.sha256(value.encode()).hexdigest()[:10]}"


def detail_path(spec: DetailSpec) -> Path:
    root = Path(HISTORY_CACHE_DIR).resolve()
    path = root / _safe_segment(spec.train_type) / _safe_segment(spec.train_number) / f"{spec.month_id}.parquet"
    if root not in path.resolve(strict=False).parents:
        raise ValueError("history cache path escapes configured root")
    return path


def remote_urls(spec: DetailSpec) -> tuple[str, str]:
    if not _MONTH_RE.fullmatch(spec.month_id):
        raise ValueError("invalid history month")
    if not re.fullmatch(r"[A-Za-z0-9._-]{1,80}", HISTORY_SOURCE_REVISION):
        raise ValueError("invalid history source revision")
    relative = f"monthly_processed_data/data-{spec.month_id}.parquet"
    return (
        f"hf://datasets/{SOURCE}/{relative}",
        f"https://huggingface.co/datasets/{SOURCE}/resolve/{HISTORY_SOURCE_REVISION}/{relative}",
    )


def _duckdb() -> Any:
    try:
        import duckdb
    except ImportError as exc:
        raise RuntimeError("duckdb_unavailable") from exc
    return duckdb


def _quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def valid_parquet(path: Path) -> tuple[bool, int]:
    if not path.is_file() or path.is_symlink() or path.stat().st_size <= 8:
        return False, 0
    try:
        con = _duckdb().connect(":memory:")
        try:
            count = int(con.execute("SELECT count(*) FROM read_parquet(?)", [str(path)]).fetchone()[0])
            names = {row[0] for row in con.execute("DESCRIBE SELECT * FROM read_parquet(?)", [str(path)]).fetchall()}
        finally:
            con.close()
    except Exception:
        return False, 0
    return set(DETAIL_COLUMNS).issubset(names), count


def _copy_filtered(source: str, target: Path, spec: DetailSpec) -> int:
    con = _duckdb().connect(":memory:")
    try:
        if source.startswith(("hf://", "https://")):
            extension_home = Path(HISTORY_CACHE_DIR).resolve().parent
            extension_home.mkdir(parents=True, exist_ok=True)
            con.execute(f"SET home_directory={_quote(str(extension_home))}")
            con.execute(f"SET http_timeout={int(HISTORY_REMOTE_TIMEOUT)}")
        columns = ",".join(f'"{name}"' for name in DETAIL_COLUMNS)
        con.execute(
            f"COPY (SELECT {columns} FROM read_parquet(?) WHERE upper(trim(cast(train_type AS VARCHAR)))=? AND trim(cast(train_number AS VARCHAR))=?) TO {_quote(str(target))} (FORMAT PARQUET, COMPRESSION ZSTD)",
            [source, spec.train_type, spec.train_number],
        )
        return int(con.execute("SELECT count(*) FROM read_parquet(?)", [str(target)]).fetchone()[0])
    finally:
        con.close()


def _download_month(url: str, directory: Path) -> Path:
    fd, name = tempfile.mkstemp(prefix="history-month-", suffix=".parquet", dir=directory)
    os.close(fd)
    path = Path(name)
    response = None
    try:
        response = curl_requests.get(
            url,
            headers={"User-Agent": "FareWeave/0.0.2"},
            impersonate="firefox",
            timeout=HISTORY_REMOTE_TIMEOUT,
            allow_redirects=True,
            stream=True,
        )
        response.raise_for_status()
        with path.open("wb") as output:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if not chunk:
                    continue
                output.write(chunk)
            output.flush()
            os.fsync(output.fileno())
        return path
    except Exception:
        path.unlink(missing_ok=True)
        raise
    finally:
        if response is not None:
            response.close()


def query_remote_month(spec: DetailSpec, target: Path) -> tuple[int, str]:
    hf_url, https_url = remote_urls(spec)
    errors: list[str] = []
    for source, method in ((hf_url, "hf_range"), (https_url, "https_range")):
        try:
            return _copy_filtered(source, target, spec), method
        except Exception as exc:
            target.unlink(missing_ok=True)
            errors.append(f"{type(exc).__name__}: {exc}")
    downloaded: Path | None = None
    try:
        downloaded = _download_month(https_url, target.parent)
        return _copy_filtered(str(downloaded), target, spec), "curl_cffi_download_fallback"
    except Exception as exc:
        errors.append(f"{type(exc).__name__}: {exc}")
        raise RuntimeError("history_source_unreachable: " + " | ".join(errors)[-1500:]) from exc
    finally:
        if downloaded:
            downloaded.unlink(missing_ok=True)


def _write_detail(spec: DetailSpec) -> Path:
    target = detail_path(spec)
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.parent.is_symlink():
        raise RuntimeError("unsafe_history_cache_path")
    temporary = target.with_name(f".{target.name}.{os.getpid()}.{threading.get_ident()}.tmp.parquet")
    temporary.unlink(missing_ok=True)
    try:
        with _remote_fill_limiter:
            row_count, method = query_remote_month(spec, temporary)
        with temporary.open("rb") as handle:
            os.fsync(handle.fileno())
        os.replace(temporary, target)
        directory_fd = os.open(target.parent, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
        cache.history_detail_put({
            "cache_key": detail_cache_key(spec), "train_type": spec.train_type,
            "train_number": spec.train_number, "year": spec.year, "month": spec.month,
            "file_path": str(target), "row_count": row_count, "file_size": target.stat().st_size,
            "source": SOURCE, "source_revision": f"{HISTORY_SOURCE_REVISION}:{method}",
            "schema_version": DETAIL_SCHEMA,
        })
        _prune_lru()
        return target
    finally:
        temporary.unlink(missing_ok=True)


def _prune_lru() -> None:
    maximum = int(HISTORY_CACHE_MAX_GB * 1024 ** 3)
    entries = cache.history_detail_entries()
    total = sum(int(item["file_size"]) for item in entries)
    root = Path(HISTORY_CACHE_DIR).resolve()
    for item in entries:
        if total <= maximum:
            break
        key, path = str(item["cache_key"]), Path(str(item["file_path"]))
        with _guard:
            if key in _active or str(path.resolve(strict=False)) in _reading:
                continue
        if path.is_symlink() or root not in path.resolve(strict=False).parents:
            continue
        try:
            size = path.stat().st_size
            path.unlink()
        except FileNotFoundError:
            size = int(item["file_size"])
        cache.history_detail_delete(key)
        total -= size


@contextmanager
def protect_detail_paths(paths: list[Path]):
    resolved = {str(path.resolve(strict=False)) for path in paths}
    with _guard:
        _reading.update(resolved)
    try:
        yield
    finally:
        with _guard:
            _reading.difference_update(resolved)


async def ensure_detail_cache(spec: DetailSpec) -> Path:
    key = detail_cache_key(spec)
    async with _locks.setdefault(key, asyncio.Lock()):
        with _guard:
            _active.add(key)
        try:
            metadata = await asyncio.to_thread(cache.history_detail_get, key)
            target = detail_path(spec)
            if metadata and Path(str(metadata["file_path"])) == target and metadata.get("schema_version") == DETAIL_SCHEMA:
                valid, _ = await asyncio.to_thread(valid_parquet, target)
                if valid:
                    return target
            target.unlink(missing_ok=True)
            return await asyncio.to_thread(_write_detail, spec)
        finally:
            with _guard:
                _active.discard(key)
