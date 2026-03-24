from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path

from backend.config import DATABASE_PATH, PRIMARY_LIBRARY_PATH
from backend.db import EEGDatabase
from backend.eeg_library import EEGLibraryService


logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger("index_eeg_library")


def main() -> None:
    db = EEGDatabase(DATABASE_PATH)
    service = EEGLibraryService(PRIMARY_LIBRARY_PATH, db)

    if not PRIMARY_LIBRARY_PATH.exists():
        logger.warning("EEG directory does not exist, creating: %s", PRIMARY_LIBRARY_PATH)
        PRIMARY_LIBRARY_PATH.mkdir(parents=True, exist_ok=True)

    all_files = [p for p in PRIMARY_LIBRARY_PATH.rglob("*") if p.is_file()]
    eeg_files = [p for p in all_files if p.suffix.lower() == ".edf"]
    skipped = [p for p in all_files if p.suffix.lower() != ".edf"]

    for p in skipped:
        logger.info("SKIPPED non-EEG: %s", p)

    inserted_or_updated = 0
    failed = 0

    for p in eeg_files:
        try:
            changed = service._index_file(p)
            if changed:
                inserted_or_updated += 1
                logger.info("INDEXED: %s", p)
            else:
                logger.info("UNCHANGED: %s", p)
        except Exception as exc:  # noqa: BLE001
            failed += 1
            logger.exception("FAILED: %s (%s)", p, exc)

    logger.info(
        "DONE scanned=%s eeg_files=%s skipped=%s failed=%s inserted_or_updated=%s db=%s",
        len(all_files),
        len(eeg_files),
        len(skipped),
        failed,
        inserted_or_updated,
        DATABASE_PATH,
    )

    # Optional JSON summary for scripts
    summary = {
        "timestamp": datetime.now(UTC).isoformat(),
        "scanned": len(all_files),
        "eeg_files": len(eeg_files),
        "skipped": len(skipped),
        "failed": failed,
        "inserted_or_updated": inserted_or_updated,
    }
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
