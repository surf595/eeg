from __future__ import annotations

from celery import Celery

from backend.core.settings import settings

celery_app = Celery("eeg_workers", broker=settings.redis_dsn, backend=settings.redis_dsn)
celery_app.conf.task_routes = {"workers.tasks.*": {"queue": "eeg"}}
