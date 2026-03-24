codex/implement-eeg-file-indexing-in-backend-hjtrsr
# EEG Library Module

Источник данных: локальная папка `./eeg` (primary data library).

## Что реализовано

### 1) File scanner
- Рекурсивное сканирование `./eeg`.
- Поиск только `.EDF`/`.edf` (case-insensitive).
- Non-EEG файлы игнорируются.

### 2) File registry
Для каждого файла в реестре хранятся:
- hash файла;
- размер;
- дата модификации;
- parser status;
- parser type.

### 3) Metadata extraction
Извлекаются поля:
- file_name;
- subject code;
- age;
- sex;
- record_type;
- stimulation frequency;
- duration;
- sampling rate;
- n_channels.

Поддержка:
- стандартный EDF parser (`edf_standard`);
- fallback parser для BrainWin-like EDF с нестандартным заголовком (`brainwin_like`).

### 4) Reindex flow
- endpoint: `POST /api/files/reindex`
- повторное сканирование `./eeg`
- добавление новых файлов
- обновление изменённых
- без дублирования

Дополнительно:
- `GET /api/files` — список файлов из реестра.

### 5) Database entities
Созданы сущности:
- Subject (`subjects`)
- EEGFile (`eeg_files`)
- EEGChannel (`eeg_channels`)
- EEGAnnotation (`eeg_annotations`)
- EEGFeatureSet (`eeg_feature_sets`)
- TextDescription (`text_descriptions`)

# EEG Research Workspace

Локальная папка `./eeg` используется как **primary data library** проекта.

## Что делает backend

- При старте автоматически сканирует `./eeg`.
- Рекурсивно индексирует `.edf` и `.EDF`.
- Для каждого файла вычисляет SHA-256, извлекает EDF metadata, определяет тип записи (`baseline`, `stimulation`, `deidentified`, `unknown`) и сохраняет в SQLite.
- Не дублирует уже проиндексированные файлы.
- Поддерживает ручной `reindex` и фоновую синхронизацию для новых файлов.

## Веб-приложение (исследовательский интерфейс)

- Просмотр сырых EEG-сигналов выбранного интервала.
- Перерасчёт признаков по выделенному сегменту.
- PSD, spectrogram, band powers, derived metrics.
- Осторожное автоматически сгенерированное психофизиологическое описание (не клинический диагноз).
- Сравнение респондент vs респондент.
- Сравнение baseline vs stimulation для одного респондента.
- Экспорт результатов в JSON/CSV.

## Важно

Этот интерфейс предназначен для исследовательской и экспертной работы.
**Не является медицинской диагностической системой.**


## Запуск

```bash
pip install -r requirements.txt
uvicorn backend.app:app --reload
```

codex/implement-eeg-file-indexing-in-backend-hjtrsr

Откройте: `http://127.0.0.1:8000/`


## Ручной reindex

```bash
python -m backend.cli reindex
```
