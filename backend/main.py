from __future__ import annotations

from fastapi import FastAPI

from backend.api.router import router
from backend.core.settings import settings

app = FastAPI(title=settings.app_name)
app.include_router(router)
