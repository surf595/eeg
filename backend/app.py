from __future__ import annotations

from threading import Event, Thread

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import BACKGROUND_SYNC_SECONDS, DATABASE_PATH, PRIMARY_LIBRARY_PATH
from .db import EEGDatabase
from .eeg_library import EEGLibraryService

db = EEGDatabase(DATABASE_PATH)
library = EEGLibraryService(PRIMARY_LIBRARY_PATH, db)

app = FastAPI(title="EEG Library Module")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_stop_event = Event()
_worker: Thread | None = None


@app.on_event("startup")
def startup() -> None:
    library.reindex()
    _start_sync()


@app.on_event("shutdown")
def shutdown() -> None:
    _stop_event.set()
    if _worker and _worker.is_alive():
        _worker.join(timeout=1)


@app.post("/api/files/reindex")
def reindex_files() -> dict:
    result = library.reindex()
    return {"scanned": result.scanned, "inserted_or_updated": result.inserted_or_updated}


@app.get("/api/files")
def list_files() -> list[dict]:
    return [dict(row) for row in db.list_files()]


def _start_sync() -> None:
    global _worker
    if _worker and _worker.is_alive():
        return
    _stop_event.clear()

    def _loop() -> None:
        while not _stop_event.wait(BACKGROUND_SYNC_SECONDS):
            library.reindex()

    _worker = Thread(target=_loop, daemon=True, name="eeg-library-sync")
    _worker.start()
