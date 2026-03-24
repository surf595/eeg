from __future__ import annotations

import json

from fastapi import FastAPI

from .service import EEGService

service = EEGService()
app = FastAPI(title="EEG Library Backend")


@app.on_event("startup")
def startup() -> None:
    service.initial_scan()
    service.start_background_sync()


@app.on_event("shutdown")
def shutdown() -> None:
    service.stop_background_sync()


@app.get("/library/files")
def list_library_files() -> list[dict]:
    return [dict(row) | {"metadata": json.loads(row["metadata_json"])} for row in service.database.list_files()]


@app.post("/library/reindex")
def reindex_library() -> dict:
    result = service.reindex()
    return {"scanned": result.scanned, "inserted_or_updated": result.inserted_or_updated}
