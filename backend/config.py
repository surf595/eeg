from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PRIMARY_LIBRARY_PATH = PROJECT_ROOT / "eeg"
DATABASE_PATH = PROJECT_ROOT / ".eeg_index.db"
BACKGROUND_SYNC_SECONDS = 30

SUPPORTED_EXTENSIONS = {".edf"}
RECORDING_TYPES = {"baseline", "stimulation", "deidentified", "unknown"}
