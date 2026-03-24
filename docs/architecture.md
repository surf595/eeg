# Architecture

- Frontend: Next.js + TypeScript + Tailwind + Plotly.
- Backend: FastAPI + NumPy + Pandas + SciPy + MNE where possible.
- Storage: PostgreSQL + local filesystem (`./eeg`).
- Async: Redis + Celery workers.

## Directories

- `/frontend`
- `/backend`
- `/workers`
- `/shared`
- `/tests`
- `/docs`
- `/eeg`
