from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Iterable


class EEGDatabase:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self._ensure_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS eeg_files (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_path TEXT NOT NULL UNIQUE,
                    file_hash TEXT NOT NULL,
                    recording_type TEXT NOT NULL,
                    metadata_json TEXT NOT NULL,
                    indexed_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(file_hash, file_path)
                )
                """
            )
            conn.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS idx_eeg_files_hash
                ON eeg_files(file_hash)
                """
            )

    def upsert_file(
        self,
        *,
        file_path: str,
        file_hash: str,
        recording_type: str,
        metadata_json: str,
        timestamp: str,
    ) -> bool:
        """Insert or update a file row. Returns True when data changed."""
        with self._connect() as conn:
            existing = conn.execute(
                "SELECT id, file_hash, recording_type, metadata_json FROM eeg_files WHERE file_path = ?",
                (file_path,),
            ).fetchone()
            if existing:
                if (
                    existing["file_hash"] == file_hash
                    and existing["recording_type"] == recording_type
                    and existing["metadata_json"] == metadata_json
                ):
                    return False
                conn.execute(
                    """
                    UPDATE eeg_files
                    SET file_hash = ?, recording_type = ?, metadata_json = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (file_hash, recording_type, metadata_json, timestamp, existing["id"]),
                )
                return True

            duplicate_hash = conn.execute(
                "SELECT id FROM eeg_files WHERE file_hash = ?",
                (file_hash,),
            ).fetchone()
            if duplicate_hash:
                # Avoid duplicate records for already indexed content.
                return False

            conn.execute(
                """
                INSERT INTO eeg_files (
                    file_path, file_hash, recording_type, metadata_json, indexed_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (file_path, file_hash, recording_type, metadata_json, timestamp, timestamp),
            )
            return True

    def list_files(self) -> Iterable[sqlite3.Row]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT file_path, file_hash, recording_type, metadata_json, indexed_at, updated_at
                FROM eeg_files
                ORDER BY file_path
                """
            ).fetchall()
        return rows
