from __future__ import annotations

from abc import ABC, abstractmethod
import re
from dataclasses import dataclass
from pathlib import Path

try:
    import pyedflib
except ImportError:  # pragma: no cover
    pyedflib = None


@dataclass
class ParsedMetadata:
    parser_status: str
    parser_type: str
    file_name: str
    subject_code: str
    age: str
    sex: str
    record_type: str
    stimulation_frequency: str
    duration: float
    sampling_rate: float
    n_channels: int


class BaseReader(ABC):
    @abstractmethod
    def can_read(self, path: Path) -> bool:
        raise NotImplementedError

    @abstractmethod
    def parse(self, path: Path) -> ParsedMetadata:
        raise NotImplementedError


class StandardEDFReader(BaseReader):
    def can_read(self, path: Path) -> bool:
        return pyedflib is not None and path.suffix.lower() == ".edf"

    def parse(self, path: Path) -> ParsedMetadata:
        if pyedflib is None:
            raise RuntimeError("pyedflib unavailable")
        with pyedflib.EdfReader(str(path)) as edf:
            labels = edf.getSignalLabels()
            fs = float(edf.getSampleFrequency(0)) if labels else 0.0
            n_samples = int(edf.getNSamples()[0]) if labels else 0
            duration = float(n_samples / fs) if fs else 0.0

            patient = (edf.getPatientCode() or "").strip()
            sex = (edf.getSex() or "").strip().upper() or "U"
            age = str(edf.getAge()) if edf.getAge() not in (None, "") else ""
            recording = (edf.getRecordingAdditional() or "").strip().lower()

            return ParsedMetadata(
                parser_status="ok",
                parser_type="edf_standard",
                file_name=path.name,
                subject_code=patient or _subject_from_name(path),
                age=age,
                sex=sex,
                record_type=_record_type(path, recording),
                stimulation_frequency=_stim_freq(path.name),
                duration=duration,
                sampling_rate=fs,
                n_channels=len(labels),
            )


class BrainWinReader(BaseReader):
    def can_read(self, path: Path) -> bool:
        return path.suffix.lower() == ".edf"

    def parse(self, path: Path) -> ParsedMetadata:
        # BrainWin-like fallback when standard EDF header is broken/non-standard.
        size = path.stat().st_size if path.exists() else 0
        sampling = 0.0
        channels = 0
        duration = 0.0

        guessed_fs = re.search(r"(\d{2,4})hz", path.stem, re.IGNORECASE)
        if guessed_fs:
            sampling = float(guessed_fs.group(1))

        guessed_channels = re.search(r"(\d{1,3})ch", path.stem, re.IGNORECASE)
        if guessed_channels:
            channels = int(guessed_channels.group(1))

        if sampling > 0 and channels > 0 and size > 0:
            approx_samples = size / 2 / channels
            duration = approx_samples / sampling

        return ParsedMetadata(
            parser_status="fallback",
            parser_type="brainwin_like",
            file_name=path.name,
            subject_code=_subject_from_name(path),
            age=_extract_age(path.stem),
            sex=_extract_sex(path.stem),
            record_type=_record_type(path, path.stem.lower()),
            stimulation_frequency=_stim_freq(path.stem),
            duration=duration,
            sampling_rate=sampling,
            n_channels=channels,
        )


class ReaderFactory:
    def __init__(self) -> None:
        self.readers: list[BaseReader] = [StandardEDFReader(), BrainWinReader()]

    def create(self, path: Path) -> BaseReader:
        for reader in self.readers:
            if reader.can_read(path):
                return reader
        return BrainWinReader()


class EEGMetadataParser:
    def __init__(self) -> None:
        self.factory = ReaderFactory()

    def parse(self, path: Path) -> ParsedMetadata:
        standard_reader = self.factory.readers[0]
        if standard_reader.can_read(path):
            try:
                return standard_reader.parse(path)
            except Exception:
                pass
        return BrainWinReader().parse(path)


def _subject_from_name(path: Path) -> str:
    base = re.split(r"[_\-.]", path.stem)[0]
    return base or "unknown"


def _extract_age(text: str) -> str:
    match = re.search(r"(?:age|a)(\d{1,3})", text, re.IGNORECASE)
    return match.group(1) if match else ""


def _extract_sex(text: str) -> str:
    low = text.lower()
    if re.search(r"(?:^|[_\-.])m(?:ale)?(?:$|[_\-.])", low):
        return "M"
    if re.search(r"(?:^|[_\-.])f(?:emale)?(?:$|[_\-.])", low):
        return "F"
    return "U"


def _record_type(path: Path, text: str) -> str:
    haystack = f"{path.stem.lower()} {text}"
    if "baseline" in haystack:
        return "baseline"
    if "stim" in haystack:
        return "stimulation"
    if "deident" in haystack or "anon" in haystack:
        return "deidentified"
    return "unknown"


def _stim_freq(text: str) -> str:
    match = re.search(r"(\d+(?:\.\d+)?)\s*hz", text, re.IGNORECASE)
    return match.group(1) if match else ""
