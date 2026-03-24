import numpy as np

from backend.signal_analysis import analyze_selection


def test_interval_analysis_respects_selection():
    fs = 50.0
    t = np.arange(0, 20, 1 / fs)
    sig = np.sin(2 * np.pi * 8 * t)
    signals = np.vstack([sig])

    out_short = analyze_selection(signals, fs, ["Cz"], 0, 5)
    out_long = analyze_selection(signals, fs, ["Cz"], 0, 15)

    assert out_short["selection"]["end"] == 5
    assert out_long["selection"]["end"] == 15
    assert out_short["spectrogram"]["times"] != out_long["spectrogram"]["times"]
