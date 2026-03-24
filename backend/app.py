from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .analysis import analyze_segment
from .config import PROJECT_ROOT
from .edf_reader import EDFReader
from .service import EEGService

service = EEGService()
app = FastAPI(title="EEG Research Workspace")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

frontend_dir = PROJECT_ROOT / "frontend"
app.mount("/static", StaticFiles(directory=frontend_dir), name="static")


class SegmentRequest(BaseModel):
    file_id: int
    channel: str = Field(default="")
    start_sec: float = Field(default=0.0, ge=0)
    duration_sec: float = Field(default=10.0, gt=0)


class CompareRequest(BaseModel):
    left_file_id: int
    right_file_id: int
    channel: str = Field(default="")
    start_sec: float = Field(default=0.0, ge=0)
    duration_sec: float = Field(default=10.0, gt=0)


@app.on_event("startup")
def startup() -> None:
    service.initial_scan()
    service.start_background_sync()


@app.on_event("shutdown")
def shutdown() -> None:
    service.stop_background_sync()


@app.get("/")
def index() -> FileResponse:
    return FileResponse(frontend_dir / "index.html")


@app.get("/library/files")
def list_library_files() -> list[dict]:
    rows = service.database.list_files()
    return [dict(row) | {"metadata": json.loads(row["metadata_json"])} for row in rows]


@app.post("/library/reindex")
def reindex_library() -> dict:
    result = service.reindex()
    return {"scanned": result.scanned, "inserted_or_updated": result.inserted_or_updated}


@app.get("/library/file/{file_id}/channels")
def list_channels(file_id: int) -> dict:
    row = _resolve_file(file_id)
    reader = EDFReader(_abs_path(row["file_path"]))
    return {"channels": reader.list_channels()}


@app.post("/analysis/segment")
def analyze_selected_segment(request: SegmentRequest) -> dict:
    row = _resolve_file(request.file_id)
    segment = _read_segment(row["file_path"], request.channel, request.start_sec, request.duration_sec)
    analysis = analyze_segment(segment.signal, segment.sample_rate)
    times = (np.arange(len(segment.signal)) / segment.sample_rate + request.start_sec).tolist()

    return {
        "file_id": request.file_id,
        "file_path": row["file_path"],
        "subject_id": row["subject_id"],
        "recording_type": row["recording_type"],
        "channel": segment.channel,
        "sample_rate": segment.sample_rate,
        "total_duration_sec": segment.total_duration_sec,
        "raw": {"times": times, "values": segment.signal.tolist()},
        "analysis": analysis.__dict__,
        "disclaimer": "Research/expert support only. Not a medical diagnostic system.",
    }


@app.post("/compare/respondents")
def compare_respondents(request: CompareRequest) -> dict:
    left = analyze_selected_segment(
        SegmentRequest(
            file_id=request.left_file_id,
            channel=request.channel,
            start_sec=request.start_sec,
            duration_sec=request.duration_sec,
        )
    )
    right = analyze_selected_segment(
        SegmentRequest(
            file_id=request.right_file_id,
            channel=request.channel,
            start_sec=request.start_sec,
            duration_sec=request.duration_sec,
        )
    )
    return _build_comparison(left, right, "respondent_vs_respondent")


@app.get("/compare/baseline-stimulation/{subject_id}")
def compare_baseline_stimulation(subject_id: str, channel: str = "", start_sec: float = 0.0, duration_sec: float = 10.0) -> dict:
    baseline, stimulation = service.database.find_subject_pair(subject_id)
    if not baseline or not stimulation:
        raise HTTPException(status_code=404, detail="Subject requires both baseline and stimulation recordings")
    left = analyze_selected_segment(SegmentRequest(file_id=int(baseline["id"]), channel=channel, start_sec=start_sec, duration_sec=duration_sec))
    right = analyze_selected_segment(
        SegmentRequest(file_id=int(stimulation["id"]), channel=channel, start_sec=start_sec, duration_sec=duration_sec)
    )
    return _build_comparison(left, right, "baseline_vs_stimulation")


@app.post("/export/analysis")
def export_analysis(request: SegmentRequest, export_format: str = "json"):
    payload = analyze_selected_segment(request)
    if export_format.lower() == "json":
        return payload
    if export_format.lower() == "csv":
        metrics = payload["analysis"]["derived_metrics"]
        csv = "metric,value\n" + "\n".join([f"{k},{v}" for k, v in metrics.items()])
        return {"csv": csv}
    raise HTTPException(status_code=400, detail="Supported formats: json, csv")


def _resolve_file(file_id: int):
    row = service.database.get_file(file_id)
    if not row:
        raise HTTPException(status_code=404, detail="Indexed EEG file not found")
    return row


def _abs_path(stored_path: str) -> Path:
    path = PROJECT_ROOT / stored_path
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"File does not exist on disk: {stored_path}")
    return path


def _read_segment(stored_path: str, channel: str, start_sec: float, duration_sec: float):
    reader = EDFReader(_abs_path(stored_path))
    try:
        return reader.read_segment(channel=channel, start_sec=start_sec, duration_sec=duration_sec)
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


def _build_comparison(left: dict, right: dict, mode: str) -> dict:
    lm = left["analysis"]["derived_metrics"]
    rm = right["analysis"]["derived_metrics"]
    metric_delta = {k: lm[k] - rm.get(k, 0.0) for k in lm.keys()}
    return {
        "mode": mode,
        "left": {
            "file_id": left["file_id"],
            "file_path": left["file_path"],
            "subject_id": left["subject_id"],
            "recording_type": left["recording_type"],
        },
        "right": {
            "file_id": right["file_id"],
            "file_path": right["file_path"],
            "subject_id": right["subject_id"],
            "recording_type": right["recording_type"],
        },
        "delta": metric_delta,
        "narrative": (
            "Automated comparison for research review only; not a clinical interpretation. "
            f"Largest absolute delta metric: {max(metric_delta, key=lambda k: abs(metric_delta[k]))}."
        ),
    }
