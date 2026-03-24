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


## Export

- `GET /api/export/file/{file_id}?format=csv`
- `GET /api/export/file/{file_id}?format=xlsx`
- `GET /api/export/file/{file_id}?format=json`
- `GET /api/export/file/{file_id}?format=pdf`
- `GET /api/export/file/{file_id}?format=png` (zip with PNG charts)
- `GET /api/export/subject/{subject_code}` (subject-level PDF report)

PDF report includes metadata, summary metrics, state name, confidence, PSD, spectrogram, raw excerpt, text description, quality flags, date and pipeline version.
