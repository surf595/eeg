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

## Запуск

```bash
pip install -r requirements.txt
uvicorn backend.app:app --reload
```

## Ручной reindex

```bash
python -m backend.cli reindex
```
