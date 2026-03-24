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
# EEG Platform

## Stack

### Frontend
- Next.js
- TypeScript
- Tailwind CSS
- Plotly.js

### Backend
- FastAPI
- Python
- NumPy
- Pandas
- SciPy
- MNE (where possible)
- custom BrainWin parser fallback

### Storage
- PostgreSQL
- local filesystem
- EEG library path = `./eeg`

### Async
- Redis
- Celery

## Repo structure

- `/frontend`
- `/backend`
- `/workers`
- `/shared`
- `/tests`
- `/docs`
- `/eeg` (existing EEG library)

## Run backend

```bash
pip install -r requirements.txt
uvicorn backend.main:app --reload
```

## Run workers

```bash
celery -A workers.celery_app.celery_app worker -Q eeg -l info
```

## Run frontend

```bash
cd frontend
npm install
npm run dev
```
# EEG Single-file Page

Источник данных: локальная библиотека `./eeg`.

## Что реализовано

- Backend EEG Library (сканер, реестр, metadata extraction, reindex).
- Single-file web page `frontend/index.html` для просмотра/анализа/сравнения EEG.

## Страница включает

1. Raw EEG viewer
   - stacked channels
   - zoom/pan
   - time cursor + start/end markers
   - amplitude scale
   - channel show/hide
   - presets by region

2. Interval selection
   - выделение через zoom по оси времени
   - start/end markers
   - Analyze selection
   - пересчёт PSD/spectrogram/metrics/text

3. PSD panel
   - selected channel
   - multi-channel overlay
   - region average

4. Spectrogram panel
   - selected channel
   - region mean
   - hover (time/frequency/power)

5. Metrics panel
   - PDR
   - alpha/theta
   - beta/alpha
   - artifact burden
   - state name
   - confidence

6. Text description panel
   - generated description (RU)
   - editable
   - save edits
   - version history

7. Comparison panel
   - baseline vs stimulation (same respondent)
   - selected file vs selected file

## API

- `POST /api/files/reindex`
- `GET /api/files`
- `GET /api/files/{file_id}/raw`
- `POST /api/analyze-selection`
- `POST /api/text/save`
- `GET /api/text/history/{file_id}`
- `GET /api/compare/baseline-stimulation/{subject_code}`
- `POST /api/compare/files`

## Запуск

```bash
pip install -r requirements.txt
uvicorn backend.app:app --reload
```

Откройте: `http://127.0.0.1:8000/`
