from __future__ import annotations

from .config import DATABASE_PATH, PRIMARY_LIBRARY_PATH
from .db import EEGDatabase
from .eeg_library import EEGLibraryService, ReindexResult


class EEGService:
    def __init__(self) -> None:
        self.database = EEGDatabase(DATABASE_PATH)
        self.library = EEGLibraryService(PRIMARY_LIBRARY_PATH, self.database)

    def initial_scan(self) -> ReindexResult:
        return self.library.reindex()

    def reindex(self) -> ReindexResult:
        return self.library.reindex()
