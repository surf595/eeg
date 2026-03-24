from __future__ import annotations

import numpy as np
from scipy import signal

REGION_PRESETS = {
    "frontal": ["Fp1", "Fp2", "F3", "F4", "F7", "F8", "Fz"],
    "central": ["C3", "C4", "Cz"],
    "parietal": ["P3", "P4", "Pz"],
    "occipital": ["O1", "O2"],
    "temporal": ["T3", "T4", "T5", "T6", "T7", "T8"],
}


def analyze_selection(signals: np.ndarray, fs: float, channel_names: list[str], start: float, end: float) -> dict:
    start_idx = max(0, int(start * fs))
    end_idx = max(start_idx + 1, min(signals.shape[1], int(end * fs)))
    seg = signals[:, start_idx:end_idx]

    psd_by_channel: dict[str, dict[str, list[float]]] = {}
    band_metrics: dict[str, dict[str, float]] = {}

    for i, name in enumerate(channel_names):
        x = signal.detrend(seg[i])
        freqs, pxx = signal.welch(x, fs=fs, nperseg=min(1024, len(x)))
        psd_by_channel[name] = {"freqs": freqs.tolist(), "power": pxx.tolist()}
        band_metrics[name] = _band_metrics(freqs, pxx)

    selected = channel_names[0] if channel_names else ""
    spec_f, spec_t, spec_sxx = signal.spectrogram(seg[0], fs=fs, nperseg=min(256, seg.shape[1])) if seg.size else (np.array([]), np.array([]), np.array([[]]))

    region_avg = _region_average(psd_by_channel)
    summary = _summary_metrics(band_metrics)

    return {
        "selection": {"start": start, "end": end},
        "psd": {
            "selected_channel": selected,
            "by_channel": psd_by_channel,
            "region_average": region_avg,
        },
        "spectrogram": {
            "selected_channel": selected,
            "frequencies": spec_f.tolist(),
            "times": spec_t.tolist(),
            "power": spec_sxx.tolist(),
            "region_mean_power": float(np.mean(spec_sxx)) if spec_sxx.size else 0.0,
        },
        "metrics": summary,
        "text_description": _text_description_ru(summary),
    }


def _band_metrics(freqs: np.ndarray, pxx: np.ndarray) -> dict[str, float]:
    def power(lo: float, hi: float) -> float:
        m = (freqs >= lo) & (freqs <= hi)
        if not np.any(m):
            return 0.0
        return float(np.trapezoid(pxx[m], freqs[m]))

    delta = power(1, 4)
    theta = power(4, 8)
    alpha = power(8, 13)
    beta = power(13, 30)
    gamma = power(30, 45)

    total = delta + theta + alpha + beta + gamma + 1e-9
    pdr = alpha / total
    artifact_burden = min(1.0, gamma / (alpha + 1e-9))

    return {
        "delta": delta,
        "theta": theta,
        "alpha": alpha,
        "beta": beta,
        "gamma": gamma,
        "pdr": pdr,
        "alpha_theta": alpha / (theta + 1e-9),
        "beta_alpha": beta / (alpha + 1e-9),
        "artifact_burden": artifact_burden,
    }


def _summary_metrics(band_metrics: dict[str, dict[str, float]]) -> dict:
    if not band_metrics:
        return {
            "PDR": 0,
            "alpha_theta": 0,
            "beta_alpha": 0,
            "artifact_burden": 0,
            "state_name": "insufficient_data",
            "confidence": 0,
        }

    arr = list(band_metrics.values())
    pdr = float(np.mean([x["pdr"] for x in arr]))
    alpha_theta = float(np.mean([x["alpha_theta"] for x in arr]))
    beta_alpha = float(np.mean([x["beta_alpha"] for x in arr]))
    artifact = float(np.mean([x["artifact_burden"] for x in arr]))

    if artifact > 0.6:
        state = "artifact_heavy"
    elif pdr > 0.25 and alpha_theta > 1.0:
        state = "alpha_dominant_resting"
    elif beta_alpha > 1.2:
        state = "beta_activated"
    else:
        state = "mixed"

    confidence = float(max(0.05, 1.0 - artifact * 0.7))
    return {
        "PDR": pdr,
        "alpha_theta": alpha_theta,
        "beta_alpha": beta_alpha,
        "artifact_burden": artifact,
        "state_name": state,
        "confidence": confidence,
    }


def _region_average(psd_by_channel: dict[str, dict[str, list[float]]]) -> dict[str, dict[str, list[float]]]:
    result = {}
    for region, channels in REGION_PRESETS.items():
        matched = [psd_by_channel[ch] for ch in channels if ch in psd_by_channel]
        if not matched:
            continue
        freqs = np.asarray(matched[0]["freqs"])
        power_stack = np.vstack([np.asarray(x["power"]) for x in matched])
        result[region] = {"freqs": freqs.tolist(), "power": power_stack.mean(axis=0).tolist()}
    return result


def _text_description_ru(summary: dict) -> str:
    return (
        "Автоматическое исследовательское описание (не медицинский диагноз). "
        f"PDR={summary['PDR']:.3f}, alpha/theta={summary['alpha_theta']:.3f}, beta/alpha={summary['beta_alpha']:.3f}, "
        f"artifact burden={summary['artifact_burden']:.3f}. "
        f"Предполагаемое состояние: {summary['state_name']}, уверенность={summary['confidence']:.2f}."
    )
