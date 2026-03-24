from backend.signal_analysis import clarity_score, profile_color


def test_comparison_ranking_score_and_color():
    better = {"PDR": 0.35, "alpha_theta": 1.6, "beta_alpha": 0.7, "artifact_burden": 0.2}
    worse = {"PDR": 0.12, "alpha_theta": 0.8, "beta_alpha": 1.4, "artifact_burden": 0.6}

    score_better = clarity_score(better)
    score_worse = clarity_score(worse)

    assert score_better > score_worse
    assert profile_color(score_better, better["artifact_burden"]) in {"green", "yellow"}
    assert profile_color(score_worse, worse["artifact_burden"]) in {"orange", "gray"}
