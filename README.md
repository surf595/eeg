# EEG backend indexing

Primary data library for EEG files is `./eeg`.

## What backend does

- Automatically scans `./eeg` on first startup.
- Recursively indexes `.edf` and `.EDF` files in all nested folders.
- For each file calculates SHA-256 hash, parses basic EDF metadata, infers recording type (`baseline`, `stimulation`, `deidentified`, `unknown`) and stores record in SQLite.
- Avoids duplicate records for already indexed files.
- Supports manual reindex command and background sync loop.

## Run

```bash
pip install -r requirements.txt
uvicorn backend.app:app --reload
```

## Reindex command

```bash
python -m backend.cli reindex
```
