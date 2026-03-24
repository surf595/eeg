from __future__ import annotations

import sqlite3
from pathlib import Path


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
