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

            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS subjects (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    code TEXT NOT NULL UNIQUE,
                    age TEXT NOT NULL DEFAULT '',
                    sex TEXT NOT NULL DEFAULT 'U',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS eeg_files (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    subject_id INTEGER NOT NULL,
                    file_path TEXT NOT NULL UNIQUE,
                    file_hash TEXT NOT NULL,
                    size_bytes INTEGER NOT NULL,
                    modified_at TEXT NOT NULL,
                    parser_status TEXT NOT NULL,
                    parser_type TEXT NOT NULL,
                    file_name TEXT NOT NULL,
                    record_type TEXT NOT NULL,
                    stimulation_frequency TEXT NOT NULL DEFAULT '',
                    duration REAL NOT NULL DEFAULT 0,
                    sampling_rate REAL NOT NULL DEFAULT 0,
                    n_channels INTEGER NOT NULL DEFAULT 0,
                    metadata_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY(subject_id) REFERENCES subjects(id)
                );

                CREATE UNIQUE INDEX IF NOT EXISTS idx_eeg_files_hash ON eeg_files(file_hash);

                CREATE TABLE IF NOT EXISTS eeg_channels (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_id INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    sampling_rate REAL NOT NULL DEFAULT 0,
                    unit TEXT NOT NULL DEFAULT '',
                    UNIQUE(file_id, name),
                    FOREIGN KEY(file_id) REFERENCES eeg_files(id)
                );

                CREATE TABLE IF NOT EXISTS eeg_annotations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_id INTEGER NOT NULL,
                    onset_sec REAL NOT NULL,
                    duration_sec REAL NOT NULL,
                    text TEXT NOT NULL,
                    FOREIGN KEY(file_id) REFERENCES eeg_files(id)
                );

                CREATE TABLE IF NOT EXISTS eeg_feature_sets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_id INTEGER NOT NULL,
                    segment_start REAL NOT NULL,
                    segment_end REAL NOT NULL,
                    features_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(file_id) REFERENCES eeg_files(id)
                );

                CREATE TABLE IF NOT EXISTS text_descriptions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_id INTEGER NOT NULL,
                    kind TEXT NOT NULL,
                    description TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(file_id) REFERENCES eeg_files(id)
                );
                """
            )

    def upsert_subject(self, *, code: str, age: str, sex: str, timestamp: str) -> int:
        with self._connect() as conn:
            row = conn.execute("SELECT id FROM subjects WHERE code = ?", (code,)).fetchone()
            if row:
                conn.execute(
                    "UPDATE subjects SET age = ?, sex = ?, updated_at = ? WHERE id = ?",
                    (age, sex, timestamp, row["id"]),
                )
                return int(row["id"])

            cur = conn.execute(
                "INSERT INTO subjects(code, age, sex, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
                (code, age, sex, timestamp, timestamp),
            )
            return int(cur.lastrowid)

    def upsert_eeg_file(self, payload: dict) -> bool:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT id, file_hash, size_bytes, modified_at, parser_status, parser_type, metadata_json FROM eeg_files WHERE file_path = ?",
                (payload["file_path"],),
            ).fetchone()

            if row:
                unchanged = (
                    row["file_hash"] == payload["file_hash"]
                    and row["size_bytes"] == payload["size_bytes"]
                    and row["modified_at"] == payload["modified_at"]
                    and row["parser_status"] == payload["parser_status"]
                    and row["parser_type"] == payload["parser_type"]
                    and row["metadata_json"] == payload["metadata_json"]
                )
                if unchanged:

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS eeg_files (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_path TEXT NOT NULL UNIQUE,
                    file_hash TEXT NOT NULL UNIQUE,
                    subject_id TEXT NOT NULL,
                    recording_type TEXT NOT NULL,
                    metadata_json TEXT NOT NULL,
                    indexed_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            columns = {row[1] for row in conn.execute("PRAGMA table_info(eeg_files)").fetchall()}
            if "subject_id" not in columns:
                conn.execute("ALTER TABLE eeg_files ADD COLUMN subject_id TEXT NOT NULL DEFAULT 'unknown'")
            if "file_hash" in columns:
                conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_eeg_files_hash ON eeg_files(file_hash)")

    def upsert_file(
        self,
        *,
        file_path: str,
        file_hash: str,
        subject_id: str,
        recording_type: str,
        metadata_json: str,
        timestamp: str,
    ) -> bool:
        with self._connect() as conn:
            existing = conn.execute(
                "SELECT id, file_hash, subject_id, recording_type, metadata_json FROM eeg_files WHERE file_path = ?",
                (file_path,),
            ).fetchone()
            if existing:
                if (
                    existing["file_hash"] == file_hash
                    and existing["subject_id"] == subject_id
                    and existing["recording_type"] == recording_type
                    and existing["metadata_json"] == metadata_json
                ):

                    return False
                conn.execute(
                    """
                    UPDATE eeg_files

                    SET subject_id = :subject_id, file_hash = :file_hash, size_bytes = :size_bytes,
                        modified_at = :modified_at, parser_status = :parser_status, parser_type = :parser_type,
                        file_name = :file_name, record_type = :record_type,
                        stimulation_frequency = :stimulation_frequency, duration = :duration,
                        sampling_rate = :sampling_rate, n_channels = :n_channels,
                        metadata_json = :metadata_json, updated_at = :updated_at
                    WHERE id = :id
                    """,
                    payload | {"id": row["id"]},
                )
                return True

            duplicate = conn.execute("SELECT id FROM eeg_files WHERE file_hash = ?", (payload["file_hash"],)).fetchone()
            if duplicate:

                    SET file_hash = ?, subject_id = ?, recording_type = ?, metadata_json = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (file_hash, subject_id, recording_type, metadata_json, timestamp, existing["id"]),
                )
                return True

            duplicate_hash = conn.execute(
                "SELECT id FROM eeg_files WHERE file_hash = ?",
                (file_hash,),
            ).fetchone()
            if duplicate_hash:
            
                return False

            conn.execute(
                """
                INSERT INTO eeg_files(
                    subject_id, file_path, file_hash, size_bytes, modified_at, parser_status, parser_type,
                    file_name, record_type, stimulation_frequency, duration, sampling_rate, n_channels,
                    metadata_json, created_at, updated_at
                ) VALUES (
                    :subject_id, :file_path, :file_hash, :size_bytes, :modified_at, :parser_status, :parser_type,
                    :file_name, :record_type, :stimulation_frequency, :duration, :sampling_rate, :n_channels,
                    :metadata_json, :created_at, :updated_at
                )
                """,
                payload,
            )
            return True

    def list_files(self) -> list[sqlite3.Row]:
        with self._connect() as conn:
            return conn.execute(
                """
                SELECT f.id, f.file_path, f.file_name, f.file_hash, f.size_bytes, f.modified_at,
                       f.parser_status, f.parser_type, f.record_type, f.stimulation_frequency,
                       f.duration, f.sampling_rate, f.n_channels,
                       s.code AS subject_code, s.age, s.sex
                FROM eeg_files f
                JOIN subjects s ON s.id = f.subject_id
                ORDER BY f.file_path
                """
            ).fetchall()

    def get_file(self, file_id: int):
        with self._connect() as conn:
            return conn.execute(
                """
                SELECT f.*, s.code AS subject_code
                FROM eeg_files f JOIN subjects s ON s.id=f.subject_id
                WHERE f.id = ?
                """,
                (file_id,),
            ).fetchone()

    def find_baseline_stimulation_pair(self, subject_code: str):
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT f.id, f.file_path, f.record_type
                FROM eeg_files f
                JOIN subjects s ON s.id=f.subject_id
                WHERE s.code = ? AND f.record_type IN ('baseline', 'stimulation')
                ORDER BY f.file_path
                """,
                (subject_code,),
            ).fetchall()
            baseline = next((r for r in rows if r['record_type'] == 'baseline'), None)
            stimulation = next((r for r in rows if r['record_type'] == 'stimulation'), None)
            return baseline, stimulation

    def add_text_description(self, *, file_id: int, kind: str, description: str, created_at: str) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO text_descriptions(file_id, kind, description, created_at) VALUES (?, ?, ?, ?)",
                (file_id, kind, description, created_at),
            )

    def get_text_history(self, file_id: int) -> list[sqlite3.Row]:
        with self._connect() as conn:
            return conn.execute(
                "SELECT id, kind, description, created_at FROM text_descriptions WHERE file_id = ? ORDER BY id DESC",
                (file_id,),
            ).fetchall()

    def add_feature_set(self, *, file_id: int, segment_start: float, segment_end: float, features_json: str, created_at: str) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO eeg_feature_sets(file_id, segment_start, segment_end, features_json, created_at) VALUES (?, ?, ?, ?, ?)",
                (file_id, segment_start, segment_end, features_json, created_at),
            )
