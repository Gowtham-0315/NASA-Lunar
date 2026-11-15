"""Unit tests for MCDA ranking, TOPSIS, and Pareto optimality."""

import pytest
from lunar_intelligence.candidate_sites import CANDIDATE_SITES
from lunar_intelligence.landing_evaluator import run_site_simulation
from lunar_intelligence.mcda_engine import evaluate_mcda, run_sensitivity_analysis


def test_mcda_evaluation():
    sites = [
        CANDIDATE_SITES["SHACKLETON_RIM"],
        CANDIDATE_SITES["MALAPERT_MOUNTAIN"],
        CANDIDATE_SITES["APOLLO11_MARE_TRANQUILLITATIS"],
    ]

    summaries = []
    for s in sites:
        _, summ = run_site_simulation(
            s,
            start_utc="2026-12-01T00:00:00Z",
            end_utc="2026-12-03T00:00:00Z",
            step_seconds=7200.0,
        )
        summaries.append((s, summ))

    ranked = evaluate_mcda(summaries)

    assert len(ranked) == 3
    assert ranked[0].rank == 1
    assert ranked[1].rank == 2
    assert ranked[2].rank == 3

    # All scores should be between 0 and 100
    for r in ranked:
        assert 0.0 <= r.wsm_score <= 100.0
        assert 0.0 <= r.topsis_score <= 100.0
        assert r.summary_verdict != ""

    # Sensitivity analysis
    sens = run_sensitivity_analysis(summaries, criterion_key="sunlight_fraction")
    assert len(sens.weight_multipliers) == 5
    assert len(sens.ranking_trajectory) == 3
