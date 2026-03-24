from __future__ import annotations


from .config import DATABASE_PATH, PRIMARY_LIBRARY_PATH
from .db import EEGDatabase
from .eeg_library import EEGLibraryService, ReindexResult

from threading import Event, Thread

from .config import BACKGROUND_SYNC_SECONDS, DATABASE_PATH, PRIMARY_LIBRARY_PATH
from .db import EEGDatabase
from .indexer import EEGIndexer, IndexingResult



class EEGService:
    def __init__(self) -> None:
        self.database = EEGDatabase(DATABASE_PATH)

        self.library = EEGLibraryService(PRIMARY_LIBRARY_PATH, self.database)

    def initial_scan(self) -> ReindexResult:
        return self.library.reindex()

    def reindex(self) -> ReindexResult:
        return self.library.reindex()

        self.indexer = EEGIndexer(PRIMARY_LIBRARY_PATH, self.database)
        self._stop_event = Event()
        self._worker: Thread | None = None

    def initial_scan(self) -> IndexingResult:
        return self.indexer.scan_and_index()

    def reindex(self) -> IndexingResult:
        return self.indexer.scan_and_index()

    def start_background_sync(self) -> None:
        if self._worker and self._worker.is_alive():
            return

        self._stop_event.clear()

        def _loop() -> None:
            while not self._stop_event.wait(BACKGROUND_SYNC_SECONDS):
                self.indexer.scan_and_index()

        self._worker = Thread(target=_loop, daemon=True, name="eeg-background-sync")
        self._worker.start()

    def stop_background_sync(self) -> None:
        self._stop_event.set()
        if self._worker and self._worker.is_alive():
            self._worker.join(timeout=1)

