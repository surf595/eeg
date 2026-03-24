from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy import signal

BANDS = {
    "delta": (1.0, 4.0),
    "theta": (4.0, 8.0),
    "alpha": (8.0, 13.0),
    "beta": (13.0, 30.0),
    "gamma": (30.0, 45.0),
}


@dataclass
class AnalysisResult:
    psd_freqs: list[float]
    psd_values: list[float]
    spectrogram_freqs: list[float]
    spectrogram_times: list[float]
    spectrogram_values: list[list[float]]
    band_powers: dict[str, float]
    derived_metrics: dict[str, float]
    narrative: str


def analyze_segment(samples: np.ndarray, fs: float) -> AnalysisResult:
    if samples.size < 8:
        raise ValueError("Segment too short for analysis")

    detrended = signal.detrend(samples)
    freqs, psd = signal.welch(detrended, fs=fs, nperseg=min(1024, len(detrended)))

    s_freqs, s_times, sxx = signal.spectrogram(
        detrended,
        fs=fs,
        nperseg=min(256, len(detrended)),
        noverlap=min(128, max(0, len(detrended) // 4)),
        scaling="density",
    )

    band_powers = _band_powers(freqs, psd)
    derived = _derived_metrics(detrended, band_powers)
    narrative = _narrative(derived, band_powers)

    max_psd_points = 512
    if len(freqs) > max_psd_points:
        idx = np.linspace(0, len(freqs) - 1, max_psd_points).astype(int)
        freqs = freqs[idx]
        psd = psd[idx]

    return AnalysisResult(
        psd_freqs=freqs.tolist(),
        psd_values=psd.tolist(),
        spectrogram_freqs=s_freqs.tolist(),
        spectrogram_times=s_times.tolist(),
        spectrogram_values=sxx.tolist(),
        band_powers=band_powers,
        derived_metrics=derived,
        narrative=narrative,
    )


def _band_powers(freqs: np.ndarray, psd: np.ndarray) -> dict[str, float]:
    bp: dict[str, float] = {}
    for name, (lo, hi) in BANDS.items():
        mask = (freqs >= lo) & (freqs <= hi)
        if not np.any(mask):
            bp[name] = 0.0
        else:
            bp[name] = float(np.trapezoid(psd[mask], freqs[mask]))
    return bp


def _derived_metrics(samples: np.ndarray, band_powers: dict[str, float]) -> dict[str, float]:
    alpha = band_powers.get("alpha", 0.0)
    beta = band_powers.get("beta", 0.0)
    theta = band_powers.get("theta", 0.0)
    delta = band_powers.get("delta", 0.0)

    total_power = float(sum(band_powers.values())) + 1e-9
    return {
        "rms": float(np.sqrt(np.mean(samples**2))),
        "variance": float(np.var(samples)),
        "alpha_beta_ratio": float(alpha / (beta + 1e-9)),
        "theta_beta_ratio": float(theta / (beta + 1e-9)),
        "slow_fast_ratio": float((delta + theta) / (alpha + beta + 1e-9)),
        "relative_alpha": float(alpha / total_power),
    }


def _narrative(derived: dict[str, float], band_powers: dict[str, float]) -> str:
    dominant_band = max(band_powers, key=band_powers.get) if band_powers else "unknown"
    caution = (
        "Automated research note (non-diagnostic): pattern-level observations only; "
        "interpret together with protocol context and expert review."
    )
    return (
        f"{caution} Dominant spectral band in selected segment: {dominant_band}. "
        f"Theta/Beta ratio: {derived['theta_beta_ratio']:.3f}, Alpha/Beta ratio: {derived['alpha_beta_ratio']:.3f}."
    )
