import numpy as np

from backend.signal_analysis import analyze_selection


def test_feature_extraction_metrics_present():
    fs = 100.0
    t = np.arange(0, 10, 1 / fs)
    sig = np.sin(2 * np.pi * 10 * t)
    signals = np.vstack([sig, sig * 0.5])

    out = analyze_selection(signals, fs, ["O1", "O2"], 0, 5, record_type="baseline", language="ru")
    metrics = out["metrics"]

    assert "PDR" in metrics
    assert "alpha_theta" in metrics
    assert "beta_alpha" in metrics
    assert "artifact_burden" in metrics
