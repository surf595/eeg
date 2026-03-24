from __future__ import annotations

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Primary EEG production data library. Can be overridden via EEG_DATA_DIR.
EEG_DATA_DIR = os.getenv("EEG_DATA_DIR", "./eeg")
PRIMARY_LIBRARY_PATH = (PROJECT_ROOT / EEG_DATA_DIR).resolve() if not Path(EEG_DATA_DIR).is_absolute() else Path(EEG_DATA_DIR)

DATABASE_PATH = PROJECT_ROOT / ".eeg_index.db"
BACKGROUND_SYNC_SECONDS = int(os.getenv("EEG_BACKGROUND_SYNC_SECONDS", "30"))

SUPPORTED_EXTENSIONS = {".edf"}
RECORDING_TYPES = {"baseline", "stimulation", "deidentified", "unknown"}
