from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np

try:
    import pyedflib
except ImportError:  # pragma: no cover
    pyedflib = None


@dataclass
class EEGSegment:
    signal: np.ndarray
    sample_rate: float
    channel: str
    total_duration_sec: float


class EDFReader:
    def __init__(self, file_path: Path) -> None:
        self.file_path = file_path

    def list_channels(self) -> list[str]:
        self._ensure_library()
        with pyedflib.EdfReader(str(self.file_path)) as edf:
            return edf.getSignalLabels()

    def read_segment(self, channel: str, start_sec: float, duration_sec: float) -> EEGSegment:
        self._ensure_library()
        with pyedflib.EdfReader(str(self.file_path)) as edf:
            labels = edf.getSignalLabels()
            if channel not in labels:
                channel = labels[0]
            idx = labels.index(channel)
            fs = float(edf.getSampleFrequency(idx))
            n_samples = int(edf.getNSamples()[idx])
            total_duration = n_samples / fs if fs else 0.0

            start = max(0, int(start_sec * fs))
            length = max(1, int(duration_sec * fs))
            end = min(n_samples, start + length)
            if end <= start:
                start = 0
                end = min(n_samples, length)

            signal = np.asarray(edf.readSignal(idx, start=start, n=end - start), dtype=np.float64)
            return EEGSegment(
                signal=signal,
                sample_rate=fs,
                channel=channel,
                total_duration_sec=total_duration,
            )

    @staticmethod
    def _ensure_library() -> None:
        if pyedflib is None:
            raise RuntimeError("pyedflib is required to read EDF files. Install dependencies from requirements.txt")
