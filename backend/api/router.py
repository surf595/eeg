from __future__ import annotations

from fastapi import APIRouter

from backend.app.web import (
    analyze,
    compare_baseline_stimulation,
    compare_files,
    compare_respondents_page,
    export_file_report,
    export_subject_report,
    get_raw,
    list_files,
    reindex_files,
    save_text,
    text_history,
)

router = APIRouter(prefix="/api")
router.add_api_route("/files/reindex", reindex_files, methods=["POST"])
router.add_api_route("/files", list_files, methods=["GET"])
router.add_api_route("/files/{file_id}/raw", get_raw, methods=["GET"])
router.add_api_route("/analyze-selection", analyze, methods=["POST"])
router.add_api_route("/text/save", save_text, methods=["POST"])
router.add_api_route("/text/history/{file_id}", text_history, methods=["GET"])
router.add_api_route("/compare/files", compare_files, methods=["POST"])
router.add_api_route("/compare/baseline-stimulation/{subject_code}", compare_baseline_stimulation, methods=["GET"])
router.add_api_route("/respondents/compare", compare_respondents_page, methods=["POST"])
router.add_api_route("/export/file/{file_id}", export_file_report, methods=["GET"])
router.add_api_route("/export/subject/{subject_code}", export_subject_report, methods=["GET"])
