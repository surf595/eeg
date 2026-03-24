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

BASELINE_RECOMMENDATIONS_RU = {
    "Спокойное бодрствование с хорошей задней альфа-организацией": "Фон выглядит устойчиво; рекомендуется поддерживать текущий режим сна, нагрузки и восстановления.",
    "Умеренно организованное бодрствование": "Состояние в пределах рабочей нормы; полезен контроль режима сна и регулярных пауз.",
    "Сниженная альфа-организация фона": "Учитывать недосып, стимуляторы, утомление; стоит проверить режим сна и нагрузку перед повторной записью.",
    "Активированное / напряжённое бодрствование": "Учитывать возможный вклад тревожности, кофеина и недовосстановления; рекомендованы техники релаксации и контроль стимуляторов.",
    "Диффузное замедление / сниженный уровень бодрствования": "Учитывать сонливость, астению и качество записи; при необходимости повторить исследование в более бодром состоянии.",
    "Неоднородная фоновая активность без отчётливой доминанты": "Наблюдается смешанный профиль; желательно сопоставить с контекстом эксперимента и повторить запись при стандартизированных условиях.",
    "Артефактно загрязнённая запись / низкая интерпретируемость": "Основной акцент — улучшение качества сигнала: электродный контакт, снижение движений и мышечных артефактов.",
}


def analyze_selection(
    signals: np.ndarray,
    fs: float,
    channel_names: list[str],
    start: float,
    end: float,
    record_type: str = "unknown",
    language: str = "ru",
) -> dict:
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

    state = _rule_state(record_type, summary)
    summary["state_name"] = state
    description = _generate_text(language=language, record_type=record_type, state=state, metrics=summary)
    recs = _recommendations(state, language)

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
        "interpretation": {
            "record_type": record_type,
            "state": state,
            "description": description,
            "recommendations": recs,
        },
        "text_description": description,
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
    return {
        "delta": delta,
        "theta": theta,
        "alpha": alpha,
        "beta": beta,
        "gamma": gamma,
        "PDR": alpha / total,
        "alpha_theta": alpha / (theta + 1e-9),
        "beta_alpha": beta / (alpha + 1e-9),
        "artifact_burden": min(1.0, gamma / (alpha + 1e-9)),
    }


def _summary_metrics(band_metrics: dict[str, dict[str, float]]) -> dict:
    if not band_metrics:
        return {"PDR": 0, "alpha_theta": 0, "beta_alpha": 0, "artifact_burden": 1, "confidence": 0}
    arr = list(band_metrics.values())
    artifact = float(np.mean([x["artifact_burden"] for x in arr]))
    return {
        "PDR": float(np.mean([x["PDR"] for x in arr])),
        "alpha_theta": float(np.mean([x["alpha_theta"] for x in arr])),
        "beta_alpha": float(np.mean([x["beta_alpha"] for x in arr])),
        "artifact_burden": artifact,
        "confidence": float(max(0.05, 1.0 - artifact * 0.7)),
    }


def _rule_state(record_type: str, m: dict) -> str:
    art = m["artifact_burden"]
    pdr = m["PDR"]
    at = m["alpha_theta"]
    ba = m["beta_alpha"]
    conf = m["confidence"]

    if art >= 0.75 or conf <= 0.25:
        return "Артефактно загрязнённая запись / низкая интерпретируемость"

    if record_type == "stimulation":
        if pdr > 0.30 and at > 1.4 and art < 0.45:
            return "Выраженное усвоение ритма стимуляции"
        if pdr > 0.23 and at > 1.1 and art < 0.55:
            return "Умеренная реакция усвоения ритма"
        if ba > 1.25 and pdr < 0.22:
            return "Сенсорная активация с десинхронизацией alpha"
        if ba > 1.05:
            return "Неспецифическая активационная реакция"
        return "Слабая / неубедительная реакция на стимуляцию"

    if pdr > 0.30 and at > 1.4 and ba < 1.0:
        return "Спокойное бодрствование с хорошей задней альфа-организацией"
    if pdr > 0.24 and at > 1.1:
        return "Умеренно организованное бодрствование"
    if pdr < 0.18 and at < 0.9 and ba < 1.05:
        return "Диффузное замедление / сниженный уровень бодрствования"
    if pdr < 0.22 and at < 1.0:
        return "Сниженная альфа-организация фона"
    if ba > 1.25:
        return "Активированное / напряжённое бодрствование"
    return "Неоднородная фоновая активность без отчётливой доминанты"


def _generate_text(language: str, record_type: str, state: str, metrics: dict) -> str:
    if language.lower().startswith("en"):
        return (
            "Automated psychophysiological note (non-diagnostic). "
            f"Recording context: {record_type}. Derived metrics: PDR={metrics['PDR']:.3f}, "
            f"alpha/theta={metrics['alpha_theta']:.3f}, beta/alpha={metrics['beta_alpha']:.3f}, "
            f"artifact burden={metrics['artifact_burden']:.3f}, confidence={metrics['confidence']:.2f}. "
            f"Rule-based state: {state}."
        )
    return (
        "Автоматическое психофизиологическое описание (не диагностическое заключение). "
        f"Контекст записи: {record_type}. Производные метрики: PDR={metrics['PDR']:.3f}, "
        f"alpha/theta={metrics['alpha_theta']:.3f}, beta/alpha={metrics['beta_alpha']:.3f}, "
        f"artifact burden={metrics['artifact_burden']:.3f}, confidence={metrics['confidence']:.2f}. "
        f"Rule-based состояние: {state}."
    )


def _recommendations(state: str, language: str) -> list[str]:
    if language.lower().startswith("en"):
        mapping = {
            k: v for k, v in BASELINE_RECOMMENDATIONS_RU.items()
        }
        return [mapping.get(state, "Interpret with protocol context; repeat in standardized conditions if needed.")]
    return [BASELINE_RECOMMENDATIONS_RU.get(state, "Интерпретировать в контексте протокола; при необходимости повторить запись в стандартизированных условиях.")]


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


def clarity_score(metrics: dict) -> float:
    return float((metrics["PDR"] * 1.4 + metrics["alpha_theta"] * 0.7 - metrics["beta_alpha"] * 0.35 - metrics["artifact_burden"] * 1.8))


def profile_color(score: float, artifact: float) -> str:
    if artifact >= 0.75:
        return "gray"
    if score >= 0.8:
        return "green"
    if score >= 0.2:
        return "yellow"
    return "orange"
