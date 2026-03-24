# EEG MVP Phase 1

## Key MVP rules

- Production EEG dataset is local `./eeg`.
- No manual upload required for MVP.
- Backend startup auto-indexes `./eeg`.
- Backend performs all signal processing.
- Frontend is visualization/UI only.
- Raw data is downsampled only for browser transfer.
- Full resolution is preserved for backend analysis/export.

## Implemented in phase 1

1. backend folder scanner indexing all EEG files from `./eeg`
2. database schema for EEG library
3. parser abstraction with BrainWin fallback (`StandardEDFReader`, `BrainWinReader`, `ReaderFactory`)
4. file catalog page (`/catalog`)
5. single-file EEG viewer page (`/viewer/[id]`)
6. interval selection and re-analysis
7. PSD + spectrogram + feature cards
8. baseline state classification
9. generated Russian text description
10. CSV/XLSX export

## Run backend

```bash
pip install -r requirements.txt
uvicorn backend.main:app --reload
```

## Run frontend

```bash
cd frontend
npm install
npm run dev
```


## Configuration

Copy `.env.example` to `.env` if needed.

Default MVP value:

```env
EEG_DATA_DIR=./eeg
```

On first backend start, the app recursively scans this folder, indexes files into DB, and exposes them in the UI catalog.
