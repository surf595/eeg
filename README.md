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
