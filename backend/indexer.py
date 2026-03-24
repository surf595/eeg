from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from .config import SUPPORTED_EXTENSIONS
from .db import EEGDatabase


@dataclass(frozen=True)
class IndexingResult:
    scanned: int
    inserted_or_updated: int


class EEGIndexer:
    def __init__(self, library_path: Path, database: EEGDatabase) -> None:
        self.library_path = library_path
        self.database = database

    def scan_and_index(self) -> IndexingResult:
        if not self.library_path.exists():
            self.library_path.mkdir(parents=True, exist_ok=True)

        scanned = 0
        changed = 0

        for file_path in self._iter_eeg_files():
            scanned += 1
            file_hash = self._sha256(file_path)
            metadata = self._parse_edf_metadata(file_path)
            recording_type = self._recording_type(file_path, metadata)
            timestamp = datetime.now(UTC).isoformat()
            updated = self.database.upsert_file(
                file_path=str(file_path.relative_to(self.library_path.parent)),
                file_hash=file_hash,
                recording_type=recording_type,
                metadata_json=json.dumps(metadata, ensure_ascii=False),
                timestamp=timestamp,
            )
            if updated:
                changed += 1

        return IndexingResult(scanned=scanned, inserted_or_updated=changed)

    def _iter_eeg_files(self):
        for path in self.library_path.rglob("*"):
            if not path.is_file():
                continue
            if path.suffix.lower() in SUPPORTED_EXTENSIONS:
                yield path

    @staticmethod
    def _sha256(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    @staticmethod
    def _parse_edf_metadata(path: Path) -> dict[str, str]:
        metadata: dict[str, str] = {"filename": path.name}
        try:
            with path.open("rb") as handle:
                header = handle.read(256)
            metadata.update(
                {
                    "version": header[0:8].decode("ascii", errors="ignore").strip(),
                    "patient_id": header[8:88].decode("ascii", errors="ignore").strip(),
                    "recording_id": header[88:168].decode("ascii", errors="ignore").strip(),
                    "start_date": header[168:176].decode("ascii", errors="ignore").strip(),
                    "start_time": header[176:184].decode("ascii", errors="ignore").strip(),
                }
            )
        except OSError:
            metadata["parse_error"] = "failed_to_read"
        return metadata

    @staticmethod
    def _recording_type(path: Path, metadata: dict[str, str]) -> str:
        haystack = " ".join([path.stem.lower(), metadata.get("recording_id", "").lower()])
        if "baseline" in haystack:
            return "baseline"
        if "stimulation" in haystack or "stim" in haystack:
            return "stimulation"
        if any(marker in haystack for marker in ("deidentified", "de-identified", "anon", "anonym")):
            return "deidentified"
        return "unknown"
