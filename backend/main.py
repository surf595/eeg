from __future__ import annotations

# Re-export the primary FastAPI application with startup auto-indexing.
from backend.app.web import app
from backend.app import app
from fastapi import FastAPI

from backend.api.router import router
from backend.core.settings import settings

app = FastAPI(title=settings.app_name)
app.include_router(router)
