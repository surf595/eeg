from __future__ import annotations

from pydantic import BaseModel


class AnalyzeSelectionRequest(BaseModel):
    file_id: int
    start_sec: float
    end_sec: float
    language: str = "ru"


class ExportRequest(BaseModel):
    file_id: int
    format: str
