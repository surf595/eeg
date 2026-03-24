# Local run (MVP)

Prerequisites:
- EEG dataset already exists in `./eeg`
- Docker (for Postgres + Redis)
- Python + Node.js

## Steps

1. Start Postgres and Redis:
   ```bash
   docker compose up -d postgres redis
   ```
2. Run backend:
   ```bash
   pip install -r requirements.txt
   uvicorn backend.main:app --reload
   ```
3. Reindex EEG library:
   ```bash
   python -m backend.app.index_eeg_library
   ```
4. Start frontend:
   ```bash
   cd frontend
   npm install
   npm run dev
   ```
5. Open catalog:
   - `http://127.0.0.1:3000/catalog`

## Expected behavior
- App automatically uses local EEG library from `EEG_DATA_DIR` (`./eeg` by default).
- No manual upload is required for initial workflow.
- Indexed files appear in catalog after startup/reindex.
