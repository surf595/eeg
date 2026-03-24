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
    language: str = "ru"


class CompareRequest(BaseModel):
    left_file_id: int
    right_file_id: int
    start_sec: float = Field(ge=0)
    end_sec: float = Field(gt=0)


class TextSaveRequest(BaseModel):
    file_id: int
    text: str
    kind: str = "manual_edit"


class RespondentCompareRequest(BaseModel):
    mode: str = "age_group"  # age_group | all
    age_group: str | None = None
    record_type: str | None = None  # baseline | stimulation
    stimulation_frequency: str | None = None


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




@app.get("/respondents")
def respondents_page() -> FileResponse:
    return FileResponse(PROJECT_ROOT / "frontend" / "respondents.html")

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

    result = analyze_selection(
        data.signals,
        fs,
        data.channels,
        req.start_sec,
        req.end_sec,
        record_type=row["record_type"],
        language=req.language,
    )
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


@app.post("/api/respondents/compare")
def compare_respondents_page(req: RespondentCompareRequest) -> dict:
    rows = [dict(r) for r in db.list_files()]

    if req.record_type:
        rows = [r for r in rows if r["record_type"] == req.record_type]
    if req.stimulation_frequency:
        rows = [r for r in rows if str(r.get("stimulation_frequency", "")) == str(req.stimulation_frequency)]

    for r in rows:
        r["age_group"] = _age_group(r.get("age", ""))

    if req.mode != "all":
        if req.age_group:
            rows = [r for r in rows if r["age_group"] == req.age_group]

    enriched = []
    for r in rows:
        file_row = db.get_file(int(r["id"]))
        path = PROJECT_ROOT / file_row["file_path"]
        if not path.exists():
            continue
        try:
            data = EDFSignalReader(path).read_all()
            if data.signals.size == 0:
                continue
            fs = float(data.sampling_rates[0])
            duration = min(20.0, data.signals.shape[1] / fs)
            res = analyze_selection(
                data.signals, fs, data.channels, 0.0, duration,
                record_type=r["record_type"], language="ru"
            )
            metrics = res["metrics"]
            state = res["interpretation"]["state"] if r["record_type"] == "baseline" else ""
            stim_summary = res["interpretation"]["state"] if r["record_type"] == "stimulation" else ""
            recommendation = "; ".join(res["interpretation"]["recommendations"])
            peak_occ = _peak_occ_freq(res["psd"]["region_average"].get("occipital") or res["psd"]["by_channel"].get(res["psd"]["selected_channel"]))
            score = _clarity_score(metrics)
            enriched.append({
                "subject": r["subject_code"],
                "age": r["age"],
                "sex": r["sex"],
                "age_group": r["age_group"],
                "baseline_state": state,
                "peak_occ_freq": peak_occ,
                "alpha_theta": metrics["alpha_theta"],
                "beta_alpha": metrics["beta_alpha"],
                "artifact_burden": metrics["artifact_burden"],
                "stimulation_summary": stim_summary,
                "recommendation": recommendation,
                "profile_color": _profile_color(score, metrics["artifact_burden"]),
                "_score": score,
            })
        except Exception:
            continue

    grouped = {}
    for e in enriched:
        grouped.setdefault(e["age_group"], []).append(e)
    for _, items in grouped.items():
        items.sort(key=lambda x: x["_score"], reverse=True)
        for i, item in enumerate(items, start=1):
            item["rank_within_age_group"] = i

    result = []
    for items in grouped.values():
        result.extend(items)
    result.sort(key=lambda x: (x["age_group"], x.get("rank_within_age_group", 999)))
    for x in result:
        x.pop("_score", None)

    return {
        "default_mode": "age_group",
        "disclaimer": "Это не рейтинг интеллекта. Это сравнение психофизиологических условий для ясного бодрствования на момент записи.",
        "rows": result,
    }


def _age_group(age: str) -> str:
    try:
        a = int(str(age).strip())
    except Exception:
        return "unknown"
    if a < 18:
        return "0-17"
    if a < 30:
        return "18-29"
    if a < 45:
        return "30-44"
    if a < 60:
        return "45-59"
    return "60+"


def _peak_occ_freq(psd: dict | None) -> float:
    if not psd:
        return 0.0
    freqs = psd.get("freqs", [])
    power = psd.get("power", [])
    if not freqs or not power:
        return 0.0
    lo, hi = 7.0, 13.5
    idx = [i for i, f in enumerate(freqs) if lo <= f <= hi]
    if not idx:
        return 0.0
    best = max(idx, key=lambda i: power[i])
    return float(freqs[best])


def _clarity_score(metrics: dict) -> float:
    return float((metrics["PDR"] * 1.4 + metrics["alpha_theta"] * 0.7 - metrics["beta_alpha"] * 0.35 - metrics["artifact_burden"] * 1.8))


def _profile_color(score: float, artifact: float) -> str:
    if artifact >= 0.75:
        return "gray"
    if score >= 0.8:
        return "green"
    if score >= 0.2:
        return "yellow"
    return "orange"
