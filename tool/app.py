from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from db_cffi_bridge import router as db_cffi_router
from reisevergleich import router as reisevergleich_router
from reisevergleich.config import APP_VERSION

ROOT = Path(__file__).resolve().parent
UI = ROOT / "ui"

app = FastAPI(
    title="FareWeave",
    version=APP_VERSION,
    description=(
        "Deterministischer multimodaler Reisevergleich mit DB/db-vendo, Split-Ticket-Prüfung, "
        "Transitous, Flix und trvl."
    ),
)
app.include_router(reisevergleich_router)
app.include_router(db_cffi_router)
app.mount("/assets", StaticFiles(directory=UI), name="assets")


@app.get("/", include_in_schema=False)
async def index() -> FileResponse:
    return FileResponse(UI / "index.html")
