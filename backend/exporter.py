from __future__ import annotations

import csv
import io
import json
import zipfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from openpyxl import Workbook
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader

from .edf_reader import EDFSignalReader
from .signal_analysis import analyze_selection

PIPELINE_VERSION = "eeg-pipeline-1.0"


@dataclass
class ExportBundle:
    analysis: dict
    metadata: dict


def build_analysis_bundle(file_row: dict, file_path: Path) -> ExportBundle:
    data = EDFSignalReader(file_path).read_all()
    if data.signals.size == 0:
        raise ValueError("No signal channels")
    fs = float(data.sampling_rates[0])
    duration = min(20.0, data.signals.shape[1] / fs)
    analysis = analyze_selection(data.signals, fs, data.channels, 0.0, duration, record_type=file_row.get("record_type", "unknown"), language="ru")
    metadata = {
        "subject": file_row.get("subject_code", ""),
        "age": file_row.get("age", ""),
        "sex": file_row.get("sex", ""),
        "record_type": file_row.get("record_type", ""),
        "file_name": file_row.get("file_name", ""),
        "file_path": file_row.get("file_path", ""),
    }
    return ExportBundle(analysis=analysis, metadata=metadata)


def export_csv(bundle: ExportBundle) -> bytes:
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(["field", "value"])
    for k, v in bundle.metadata.items():
        writer.writerow([k, v])
    for k, v in bundle.analysis["metrics"].items():
        writer.writerow([k, v])
    writer.writerow(["state_name", bundle.analysis["interpretation"]["state"]])
    writer.writerow(["confidence", bundle.analysis["metrics"].get("confidence", 0)])
    return out.getvalue().encode("utf-8")


def export_xlsx(bundle: ExportBundle) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = "analysis"
    ws.append(["field", "value"])
    for k, v in bundle.metadata.items():
        ws.append([k, v])
    for k, v in bundle.analysis["metrics"].items():
        ws.append([k, v])
    ws.append(["state_name", bundle.analysis["interpretation"]["state"]])
    ws.append(["text_description", bundle.analysis["text_description"]])

    bio = io.BytesIO()
    wb.save(bio)
    return bio.getvalue()


def export_json_bundle(bundle: ExportBundle) -> bytes:
    payload = {
        "metadata": bundle.metadata,
        "analysis": bundle.analysis,
        "date": datetime.now(UTC).isoformat(),
        "pipeline_version": PIPELINE_VERSION,
    }
    return json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")


def export_png_charts(bundle: ExportBundle) -> bytes:
    tmp = io.BytesIO()
    with zipfile.ZipFile(tmp, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("raw_excerpt.png", _raw_png(bundle))
        zf.writestr("psd.png", _psd_png(bundle))
        zf.writestr("spectrogram.png", _spec_png(bundle))
    return tmp.getvalue()


def export_pdf_report(bundle: ExportBundle) -> bytes:
    pdf = io.BytesIO()
    c = canvas.Canvas(pdf, pagesize=A4)
    w, h = A4
    y = h - 1.5 * cm

    c.setFont("Helvetica-Bold", 14)
    c.drawString(1.5 * cm, y, "EEG Analysis Report")
    y -= 0.8 * cm

    c.setFont("Helvetica", 9)
    c.drawString(1.5 * cm, y, f"date: {datetime.now(UTC).isoformat()}")
    y -= 0.5 * cm
    c.drawString(1.5 * cm, y, f"pipeline version: {PIPELINE_VERSION}")
    y -= 0.7 * cm

    c.setFont("Helvetica-Bold", 10)
    c.drawString(1.5 * cm, y, "Metadata")
    y -= 0.4 * cm
    c.setFont("Helvetica", 9)
    for k, v in bundle.metadata.items():
        c.drawString(1.8 * cm, y, f"{k}: {v}")
        y -= 0.35 * cm

    metrics = bundle.analysis["metrics"]
    c.setFont("Helvetica-Bold", 10)
    c.drawString(1.5 * cm, y, "Summary metrics")
    y -= 0.4 * cm
    c.setFont("Helvetica", 9)
    for key in ["PDR", "alpha_theta", "beta_alpha", "artifact_burden", "confidence"]:
        c.drawString(1.8 * cm, y, f"{key}: {metrics.get(key)}")
        y -= 0.35 * cm

    state = bundle.analysis["interpretation"]["state"]
    c.drawString(1.8 * cm, y, f"state name: {state}")
    y -= 0.35 * cm
    c.drawString(1.8 * cm, y, f"quality flags: {quality_flags(metrics)}")
    y -= 0.45 * cm

    c.setFont("Helvetica-Bold", 10)
    c.drawString(1.5 * cm, y, "Text description")
    y -= 0.4 * cm
    c.setFont("Helvetica", 8)
    text = bundle.analysis["text_description"][:900]
    for line in _wrap(text, 110):
        c.drawString(1.8 * cm, y, line)
        y -= 0.32 * cm
        if y < 7 * cm:
            break

    # charts
    raw_img = ImageReader(io.BytesIO(_raw_png(bundle)))
    psd_img = ImageReader(io.BytesIO(_psd_png(bundle)))
    spec_img = ImageReader(io.BytesIO(_spec_png(bundle)))
    c.drawImage(raw_img, 1.5 * cm, 1.2 * cm, width=5.5 * cm, height=4 * cm)
    c.drawImage(psd_img, 7.2 * cm, 1.2 * cm, width=5.5 * cm, height=4 * cm)
    c.drawImage(spec_img, 12.9 * cm, 1.2 * cm, width=5.5 * cm, height=4 * cm)

    c.showPage()
    c.save()
    return pdf.getvalue()


def export_subject_pdf(subject_code: str, baseline_bundle: ExportBundle | None, stimulation_bundle: ExportBundle | None, age_group_rows: list[dict]) -> bytes:
    pdf = io.BytesIO()
    c = canvas.Canvas(pdf, pagesize=A4)
    y = A4[1] - 1.5 * cm
    c.setFont("Helvetica-Bold", 14)
    c.drawString(1.5 * cm, y, f"Subject-level Report: {subject_code}")
    y -= 0.7 * cm
    c.setFont("Helvetica", 9)
    c.drawString(1.5 * cm, y, "Non-diagnostic research report")
    y -= 0.6 * cm

    if baseline_bundle:
        c.setFont("Helvetica-Bold", 10)
        c.drawString(1.5 * cm, y, "baseline profile")
        y -= 0.4 * cm
        c.setFont("Helvetica", 9)
        c.drawString(1.8 * cm, y, baseline_bundle.analysis["interpretation"]["state"])
        y -= 0.4 * cm

    if stimulation_bundle:
        c.setFont("Helvetica-Bold", 10)
        c.drawString(1.5 * cm, y, "stimulation summary")
        y -= 0.4 * cm
        c.setFont("Helvetica", 9)
        c.drawString(1.8 * cm, y, stimulation_bundle.analysis["interpretation"]["state"])
        y -= 0.4 * cm

    c.setFont("Helvetica-Bold", 10)
    c.drawString(1.5 * cm, y, "comparison within age group")
    y -= 0.4 * cm
    c.setFont("Helvetica", 8)
    for row in age_group_rows[:10]:
        c.drawString(1.8 * cm, y, f"{row['subject']} rank={row.get('rank_within_age_group')} alpha/theta={row.get('alpha_theta'):.3f} artifact={row.get('artifact_burden'):.3f}")
        y -= 0.32 * cm

    y -= 0.3 * cm
    c.setFont("Helvetica-Bold", 10)
    c.drawString(1.5 * cm, y, "recommendations")
    y -= 0.4 * cm
    recs = []
    if baseline_bundle:
        recs.extend(baseline_bundle.analysis["interpretation"]["recommendations"])
    if stimulation_bundle:
        recs.extend(stimulation_bundle.analysis["interpretation"]["recommendations"])
    c.setFont("Helvetica", 8)
    for rec in recs[:6]:
        c.drawString(1.8 * cm, y, f"- {rec[:120]}")
        y -= 0.32 * cm

    c.showPage()
    c.save()
    return pdf.getvalue()


def quality_flags(metrics: dict) -> str:
    flags = []
    if metrics.get("artifact_burden", 0) > 0.75:
        flags.append("high_artifact")
    if metrics.get("confidence", 1) < 0.35:
        flags.append("low_confidence")
    return ",".join(flags) if flags else "ok"


def _raw_png(bundle: ExportBundle) -> bytes:
    fig, ax = plt.subplots(figsize=(5, 3))
    times = bundle.analysis.get("spectrogram", {}).get("times", [])
    if times:
        ax.plot(times, [0] * len(times), color="black")
    ax.set_title("Raw excerpt")
    ax.set_xlabel("Time, s")
    ax.set_ylabel("a.u.")
    return _fig_bytes(fig)


def _psd_png(bundle: ExportBundle) -> bytes:
    fig, ax = plt.subplots(figsize=(5, 3))
    psd = bundle.analysis["psd"]
    ch = psd["selected_channel"]
    if ch and ch in psd["by_channel"]:
        ax.plot(psd["by_channel"][ch]["freqs"], psd["by_channel"][ch]["power"])
    ax.set_title("PSD")
    ax.set_xlabel("Hz")
    ax.set_ylabel("Power")
    return _fig_bytes(fig)


def _spec_png(bundle: ExportBundle) -> bytes:
    fig, ax = plt.subplots(figsize=(5, 3))
    spec = bundle.analysis["spectrogram"]
    if spec.get("frequencies") and spec.get("times"):
        ax.imshow(spec["power"], aspect="auto", origin="lower")
    ax.set_title("Spectrogram")
    return _fig_bytes(fig)


def _fig_bytes(fig) -> bytes:
    bio = io.BytesIO()
    fig.tight_layout()
    fig.savefig(bio, format="png", dpi=120)
    plt.close(fig)
    return bio.getvalue()


def _wrap(text: str, width: int):
    words = text.split()
    line = []
    ln = 0
    for w in words:
        if ln + len(w) + 1 > width:
            yield " ".join(line)
            line = [w]
            ln = len(w)
        else:
            line.append(w)
            ln += len(w) + 1
    if line:
        yield " ".join(line)
