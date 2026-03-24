from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from threading import Event, Thread

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from .config import BACKGROUND_SYNC_SECONDS, DATABASE_PATH, PRIMARY_LIBRARY_PATH, PROJECT_ROOT
from .db import EEGDatabase
from .edf_reader import EDFSignalReader
from .eeg_library import EEGLibraryService
from .signal_analysis import analyze_selection

db = EEGDatabase(DATABASE_PATH)
library = EEGLibraryService(PRIMARY_LIBRARY_PATH, db)

app = FastAPI(title="EEG Single-File Page")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

_stop_event = Event()
_worker: Thread | None = None


class AnalyzeRequest(BaseModel):
    file_id: int
    start_sec: float = Field(ge=0)
    end_sec: float = Field(gt=0)


class CompareRequest(BaseModel):
    left_file_id: int
    right_file_id: int
    start_sec: float = Field(ge=0)
    end_sec: float = Field(gt=0)


class TextSaveRequest(BaseModel):
    file_id: int
    text: str
    kind: str = "manual_edit"


@app.on_event("startup")
def startup() -> None:
    library.reindex()
    _start_sync()


@app.on_event("shutdown")
def shutdown() -> None:
    _stop_event.set()
    if _worker and _worker.is_alive():
        _worker.join(timeout=1)


@app.get("/")
def index_page() -> FileResponse:
    return FileResponse(PROJECT_ROOT / "frontend" / "index.html")


@app.post("/api/files/reindex")
def reindex_files() -> dict:
    result = library.reindex()
    return {"scanned": result.scanned, "inserted_or_updated": result.inserted_or_updated}


@app.get("/api/files")
def list_files() -> list[dict]:
    return [dict(row) for row in db.list_files()]


@app.get("/api/files/{file_id}/raw")
def get_raw(file_id: int, amplitude_scale: float = 1.0) -> dict:
    row = db.get_file(file_id)
    if not row:
        raise HTTPException(status_code=404, detail="File not found")
    path = PROJECT_ROOT / row["file_path"]
    if not path.exists():
        raise HTTPException(status_code=404, detail="File missing on disk")

    data = EDFSignalReader(path).read_all()
    if data.signals.size == 0:
        return {"channels": [], "times": [], "stacked": [], "sampling_rate": 0}

    fs = float(data.sampling_rates[0])
    times = (list(range(data.signals.shape[1])))
    times = [t / fs for t in times]

    # stacked channels with spacing and amplitude scale
    spacing = max(1.0, float(data.signals.std()) * 5)
    stacked = []
    for i, ch in enumerate(data.channels):
        y = (data.signals[i] * amplitude_scale) + i * spacing
        stacked.append({"channel": ch, "values": y.tolist()})

    return {
        "channels": data.channels,
        "times": times,
        "stacked": stacked,
        "sampling_rate": fs,
        "region_presets": {
            "frontal": ["Fp1", "Fp2", "F3", "F4", "F7", "F8", "Fz"],
            "central": ["C3", "C4", "Cz"],
            "parietal": ["P3", "P4", "Pz"],
            "occipital": ["O1", "O2"],
            "temporal": ["T3", "T4", "T5", "T6", "T7", "T8"],
        },
    }


@app.post("/api/analyze-selection")
def analyze(req: AnalyzeRequest) -> dict:
    row = db.get_file(req.file_id)
    if not row:
        raise HTTPException(status_code=404, detail="File not found")

    path = PROJECT_ROOT / row["file_path"]
    data = EDFSignalReader(path).read_all()
    if data.signals.size == 0:
        raise HTTPException(status_code=400, detail="No channels available")
    fs = float(data.sampling_rates[0])

    result = analyze_selection(data.signals, fs, data.channels, req.start_sec, req.end_sec)
    db.add_text_description(
        file_id=req.file_id,
        kind="auto_generated",
        description=result["text_description"],
        created_at=datetime.now(UTC).isoformat(),
    )
    return result


@app.post("/api/text/save")
def save_text(req: TextSaveRequest) -> dict:
    if not db.get_file(req.file_id):
        raise HTTPException(status_code=404, detail="File not found")
    db.add_text_description(file_id=req.file_id, kind=req.kind, description=req.text, created_at=datetime.now(UTC).isoformat())
    return {"status": "ok"}


@app.get("/api/text/history/{file_id}")
def text_history(file_id: int) -> list[dict]:
    return [dict(x) for x in db.get_text_history(file_id)]


@app.get("/api/compare/baseline-stimulation/{subject_code}")
def compare_baseline_stimulation(subject_code: str, start_sec: float = 0.0, end_sec: float = 10.0) -> dict:
    baseline, stimulation = db.find_baseline_stimulation_pair(subject_code)
    if not baseline or not stimulation:
        raise HTTPException(status_code=404, detail="Need baseline and stimulation files")
    return _compare(int(baseline["id"]), int(stimulation["id"]), start_sec, end_sec, mode="baseline_vs_stimulation")


@app.post("/api/compare/files")
def compare_files(req: CompareRequest) -> dict:
    return _compare(req.left_file_id, req.right_file_id, req.start_sec, req.end_sec, mode="file_vs_file")


def _compare(left_id: int, right_id: int, start: float, end: float, mode: str) -> dict:
    left = analyze(AnalyzeRequest(file_id=left_id, start_sec=start, end_sec=end))
    right = analyze(AnalyzeRequest(file_id=right_id, start_sec=start, end_sec=end))
    lm = left["metrics"]
    rm = right["metrics"]
    keys = ["PDR", "alpha_theta", "beta_alpha", "artifact_burden", "confidence"]
    delta = {k: lm[k] - rm[k] for k in keys}
    return {
        "mode": mode,
        "left_file_id": left_id,
        "right_file_id": right_id,
        "delta": delta,
        "narrative_ru": "Сравнение автоматически рассчитано для исследовательского использования. Не является медицинским заключением.",
    }


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
