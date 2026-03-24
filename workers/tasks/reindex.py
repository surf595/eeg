from __future__ import annotations

from workers.celery_app import celery_app
from backend.service import EEGService


@celery_app.task(name="workers.tasks.reindex_library")
def reindex_library() -> dict:
    service = EEGService()
    result = service.reindex()
    return {"scanned": result.scanned, "inserted_or_updated": result.inserted_or_updated}
