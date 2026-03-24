from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from .db import EEGDatabase
from .parser import EEGMetadataParser


@dataclass(frozen=True)
class ReindexResult:
    scanned: int
    inserted_or_updated: int


class EEGFileScanner:
    def __init__(self, root: Path) -> None:
        self.root = root

    def iter_eeg_files(self):
        if not self.root.exists():
            self.root.mkdir(parents=True, exist_ok=True)
        for path in self.root.rglob("*"):
            if path.is_file() and path.suffix.lower() == ".edf":
                yield path


class EEGLibraryService:
    def __init__(self, root: Path, db: EEGDatabase) -> None:
        self.root = root
        self.db = db
        self.scanner = EEGFileScanner(root)
        self.parser = EEGMetadataParser()

    def reindex(self) -> ReindexResult:
        scanned = 0
        changed = 0
        for path in self.scanner.iter_eeg_files():
            scanned += 1
            if self._index_file(path):
                changed += 1
        return ReindexResult(scanned=scanned, inserted_or_updated=changed)

    def _index_file(self, path: Path) -> bool:
        file_hash = self._sha256(path)
        stat = path.stat()
        timestamp = datetime.now(UTC).isoformat()
        metadata = self.parser.parse(path)

        subject_id = self.db.upsert_subject(
            code=metadata.subject_code,
            age=metadata.age,
            sex=metadata.sex,
            timestamp=timestamp,
        )

        payload = {
            "subject_id": subject_id,
            "file_path": str(path.relative_to(self.root.parent)),
            "file_hash": file_hash,
            "size_bytes": int(stat.st_size),
            "modified_at": datetime.fromtimestamp(stat.st_mtime, tz=UTC).isoformat(),
            "parser_status": metadata.parser_status,
            "parser_type": metadata.parser_type,
            "file_name": metadata.file_name,
            "record_type": metadata.record_type,
            "stimulation_frequency": metadata.stimulation_frequency,
            "duration": float(metadata.duration),
            "sampling_rate": float(metadata.sampling_rate),
            "n_channels": int(metadata.n_channels),
            "metadata_json": json.dumps(metadata.__dict__, ensure_ascii=False),
            "created_at": timestamp,
            "updated_at": timestamp,
        }
        return self.db.upsert_eeg_file(payload)

    @staticmethod
    def _sha256(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()
