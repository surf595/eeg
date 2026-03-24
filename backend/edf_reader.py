from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np

try:
    import pyedflib
except ImportError:  # pragma: no cover
    pyedflib = None


@dataclass
class EEGData:
    channels: list[str]
    sampling_rates: list[float]
    signals: np.ndarray  # shape: channels x samples


class EDFSignalReader:
    def __init__(self, path: Path) -> None:
        self.path = path

    def read_all(self, max_channels: int = 32) -> EEGData:
        self._ensure_lib()
        with pyedflib.EdfReader(str(self.path)) as edf:
            labels = edf.getSignalLabels()[:max_channels]
            signals = []
            sample_rates = []
            min_len = None
            for idx, ch in enumerate(labels):
                sig = np.asarray(edf.readSignal(idx), dtype=np.float64)
                fs = float(edf.getSampleFrequency(idx))
                sample_rates.append(fs)
                min_len = len(sig) if min_len is None else min(min_len, len(sig))
                signals.append(sig)

            if min_len is None:
                return EEGData(channels=[], sampling_rates=[], signals=np.zeros((0, 0)))

            cropped = np.vstack([s[:min_len] for s in signals])
            return EEGData(channels=labels, sampling_rates=sample_rates, signals=cropped)

    @staticmethod
    def _ensure_lib() -> None:
        if pyedflib is None:
            raise RuntimeError("pyedflib is required. Install requirements.txt")
