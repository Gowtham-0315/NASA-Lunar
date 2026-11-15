"""Multi-Criteria Decision Analysis (MCDA) engine: WSM, TOPSIS, AHP, Pareto Front, and Sensitivity Analysis."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

from .coordinates import LunarSite
from .landing_evaluator import SiteWindowSummary


@dataclass(frozen=True)
class McdaCriterion:
    """Definition of an MCDA evaluation criterion."""
    key: str
    name: str
    weight: float
    is_benefit: bool  # True if higher is better; False if lower is better (cost)
    description: str


@dataclass(frozen=True)
class ScoredSiteRecord:
    """Ranked landing site record with complete metric breakdown and explanations."""
    rank: int
    site_id: str
    site_name: str
    region: str
    wsm_score: float              # 0.0 to 100.0
    topsis_score: float           # 0.0 to 100.0 (relative closeness)
    is_pareto_optimal: bool
    
    # Raw values
    sunlight_fraction: float
    longest_continuous_sunlight_hours: float
    earth_los_fraction: float
    co_visibility_fraction: float
    mean_slope_deg: float
    roughness_score: float
    scientific_priority: float
    total_landing_window_hours: float
    
    # Normalized scores (0 to 1)
    norm_scores: Dict[str, float]
    score_contributions: Dict[str, float]
    summary_verdict: str


@dataclass(frozen=True)
class SensitivityRun:
    """Evaluation of how site rankings change as a single criterion weight varies."""
    criterion_key: str
    weight_multipliers: List[float]  # e.g. [0.5, 0.75, 1.0, 1.25, 1.5]
    ranking_trajectory: Dict[str, List[int]]  # site_id -> list of ranks


DEFAULT_CRITERIA: List[McdaCriterion] = [
    McdaCriterion("sunlight_fraction", "Sunlight Availability", 0.25, True, "Fraction of mission period with active solar illumination"),
    McdaCriterion("longest_continuous_sunlight", "Max Continuous Sunlight", 0.15, True, "Longest continuous lit duration for thermal/power buffer"),
    McdaCriterion("earth_los_fraction", "Direct Earth LOS", 0.20, True, "Fraction of time Earth is in clear line-of-sight for teleoperation"),
    McdaCriterion("co_visibility_fraction", "Co-Visibility (Sun & Earth)", 0.15, True, "Simultaneous solar power generation and Earth contact"),
    McdaCriterion("slope_safety", "Terrain Slope Safety", 0.15, False, "Local surface tilt angle (< 10° nominal, < 15° threshold)"),
    McdaCriterion("science_priority", "Volatiles Science Priority", 0.10, True, "Proximity to water ice cold-traps & geological value"),
]


def normalize_matrix(
    data: List[Dict[str, float]], criteria: List[McdaCriterion]
) -> List[Dict[str, float]]:
    """Linear min-max normalization for benefit and cost criteria."""
    normalized: List[Dict[str, float]] = []

    # Find min and max for each criterion
    extrema: Dict[str, Tuple[float, float]] = {}
    for crit in criteria:
        vals = [row[crit.key] for row in data]
        min_v = min(vals)
        max_v = max(vals)
        extrema[crit.key] = (min_v, max_v)

    for row in data:
        norm_row: Dict[str, float] = {}
        for crit in criteria:
            val = row[crit.key]
            min_v, max_v = extrema[crit.key]
            span = max_v - min_v if max_v != min_v else 1.0

            if crit.is_benefit:
                norm_val = (val - min_v) / span
            else:
                # Cost criterion (e.g. slope): lower is better
                norm_val = (max_v - val) / span

            norm_row[crit.key] = max(0.0, min(1.0, norm_val))
        normalized.append(norm_row)

    return normalized


def compute_topsis(
    data: List[Dict[str, float]], criteria: List[McdaCriterion]
) -> List[float]:
    """Compute TOPSIS relative closeness coefficients."""
    n_sites = len(data)
    if n_sites == 0:
        return []
    if n_sites == 1:
        return [1.0]

    # Vector normalization: denom = sqrt(sum(x_ij^2))
    denoms: Dict[str, float] = {}
    for crit in criteria:
        sq_sum = sum(row[crit.key] ** 2 for row in data)
        denoms[crit.key] = math.sqrt(sq_sum) if sq_sum > 0 else 1.0

    # Weighted normalized values
    weighted_matrix: List[Dict[str, float]] = []
    for row in data:
        w_row: Dict[str, float] = {}
        for crit in criteria:
            val = row[crit.key]
            norm_val = val / denoms[crit.key]
            w_row[crit.key] = norm_val * crit.weight
        weighted_matrix.append(w_row)

    # Positive ideal (A+) and negative ideal (A-) solutions
    ideal_pos: Dict[str, float] = {}
    ideal_neg: Dict[str, float] = {}

    for crit in criteria:
        col_vals = [w_row[crit.key] for w_row in weighted_matrix]
        if crit.is_benefit:
            ideal_pos[crit.key] = max(col_vals)
            ideal_neg[crit.key] = min(col_vals)
        else:
            ideal_pos[crit.key] = min(col_vals)
            ideal_neg[crit.key] = max(col_vals)

    # Distance to ideal solutions
    closeness_scores: List[float] = []
    for w_row in weighted_matrix:
        d_pos = math.sqrt(sum((w_row[c.key] - ideal_pos[c.key]) ** 2 for c in criteria))
        d_neg = math.sqrt(sum((w_row[c.key] - ideal_neg[c.key]) ** 2 for c in criteria))
        denom = d_pos + d_neg
        c_star = d_neg / denom if denom > 0 else 0.5
        closeness_scores.append(c_star)

    return closeness_scores


def find_pareto_frontier(data: List[Dict[str, float]], criteria: List[McdaCriterion]) -> List[bool]:
    """Identify non-dominated solutions on the Pareto frontier."""
    n = len(data)
    is_pareto = [True] * n

    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            # Check if j dominates i
            # j dominates i if j is >= i in all benefit criteria (<= for cost)
            # and strictly better in at least one
            better_or_equal = True
            strictly_better = False

            for crit in criteria:
                val_i = data[i][crit.key]
                val_j = data[j][crit.key]

                if crit.is_benefit:
                    if val_j < val_i - 1e-6:
                        better_or_equal = False
                        break
                    elif val_j > val_i + 1e-6:
                        strictly_better = True
                else:
                    if val_j > val_i + 1e-6:
                        better_or_equal = False
                        break
                    elif val_j < val_i - 1e-6:
                        strictly_better = True

            if better_or_equal and strictly_better:
                is_pareto[i] = False
                break

    return is_pareto


def evaluate_mcda(
    site_summaries: List[Tuple[LunarSite, SiteWindowSummary]],
    custom_weights: Dict[str, float] | None = None,
) -> List[ScoredSiteRecord]:
    """Run full MCDA ranking combining WSM, TOPSIS, and Pareto optimality."""
    if not site_summaries:
        return []

    # Configure criteria with custom weights if provided
    criteria: List[McdaCriterion] = []
    total_w = 0.0
    for c in DEFAULT_CRITERIA:
        w = custom_weights.get(c.key, c.weight) if custom_weights else c.weight
        criteria.append(McdaCriterion(c.key, c.name, max(0.01, w), c.is_benefit, c.description))
        total_w += max(0.01, w)

    # Normalize weights so sum = 1.0
    criteria = [
        McdaCriterion(c.key, c.name, c.weight / total_w, c.is_benefit, c.description)
        for c in criteria
    ]

    # Build raw data table
    raw_rows: List[Dict[str, float]] = []
    for site, summ in site_summaries:
        row = {
            "sunlight_fraction": summ.sunlight_fraction,
            "longest_continuous_sunlight": summ.longest_continuous_sunlight_hours,
            "earth_los_fraction": summ.earth_los_fraction,
            "co_visibility_fraction": summ.co_visibility_fraction,
            "slope_safety": site.mean_slope_deg,
            "science_priority": site.scientific_priority,
        }
        raw_rows.append(row)

    # Compute normalization & algorithms
    norm_rows = normalize_matrix(raw_rows, criteria)
    topsis_scores = compute_topsis(raw_rows, criteria)
    pareto_mask = find_pareto_frontier(raw_rows, criteria)

    # Compute WSM scores
    records: List[ScoredSiteRecord] = []
    for i, (site, summ) in enumerate(site_summaries):
        norm = norm_rows[i]
        wsm_val = sum(norm[c.key] * c.weight for c in criteria) * 100.0
        topsis_val = topsis_scores[i] * 100.0

        contributions: Dict[str, float] = {}
        for c in criteria:
            contributions[c.key] = round(norm[c.key] * c.weight * 100.0, 2)

        # Verdict synthesis
        if wsm_val >= 80.0:
            verdict = "PRIME CANDIDATE: Exceptional illumination, stable communications, and manageable slopes."
        elif wsm_val >= 60.0:
            verdict = "HIGHLY VIABLE: Strong mission profile with minor operational terrain/power tradeoffs."
        elif wsm_val >= 45.0:
            verdict = "CONDITIONALLY VIABLE: Specific science rewards offset by intermittent comms or slope constraints."
        else:
            verdict = "HAZARDOUS / MARGINAL: Significant terrain shadow, libration dips, or steep slopes."

        records.append(
            ScoredSiteRecord(
                rank=0,  # Assigned after sorting
                site_id=site.site_id,
                site_name=site.name,
                region=site.region,
                wsm_score=round(wsm_val, 2),
                topsis_score=round(topsis_val, 2),
                is_pareto_optimal=pareto_mask[i],
                sunlight_fraction=summ.sunlight_fraction,
                longest_continuous_sunlight_hours=summ.longest_continuous_sunlight_hours,
                earth_los_fraction=summ.earth_los_fraction,
                co_visibility_fraction=summ.co_visibility_fraction,
                mean_slope_deg=site.mean_slope_deg,
                roughness_score=site.roughness_score,
                scientific_priority=site.scientific_priority,
                total_landing_window_hours=summ.total_landing_window_hours,
                norm_scores={k: round(v, 4) for k, v in norm.items()},
                score_contributions=contributions,
                summary_verdict=verdict,
            )
        )

    # Sort descending by WSM score
    records.sort(key=lambda r: r.wsm_score, reverse=True)

    # Assign ranks
    final_records: List[ScoredSiteRecord] = []
    for rank_idx, rec in enumerate(records, start=1):
        final_records.append(
            ScoredSiteRecord(
                rank=rank_idx,
                site_id=rec.site_id,
                site_name=rec.site_name,
                region=rec.region,
                wsm_score=rec.wsm_score,
                topsis_score=rec.topsis_score,
                is_pareto_optimal=rec.is_pareto_optimal,
                sunlight_fraction=rec.sunlight_fraction,
                longest_continuous_sunlight_hours=rec.longest_continuous_sunlight_hours,
                earth_los_fraction=rec.earth_los_fraction,
                co_visibility_fraction=rec.co_visibility_fraction,
                mean_slope_deg=rec.mean_slope_deg,
                roughness_score=rec.roughness_score,
                scientific_priority=rec.scientific_priority,
                total_landing_window_hours=rec.total_landing_window_hours,
                norm_scores=rec.norm_scores,
                score_contributions=rec.score_contributions,
                summary_verdict=rec.summary_verdict,
            )
        )

    return final_records


def run_sensitivity_analysis(
    site_summaries: List[Tuple[LunarSite, SiteWindowSummary]],
    criterion_key: str = "sunlight_fraction",
) -> SensitivityRun:
    """Modulate a criterion weight across multipliers to analyze ranking stability."""
    multipliers = [0.5, 0.75, 1.0, 1.25, 1.5]
    ranking_trajectory: Dict[str, List[int]] = {s.site_id: [] for s, _ in site_summaries}

    base_weights = {c.key: c.weight for c in DEFAULT_CRITERIA}

    for mult in multipliers:
        perturbed = dict(base_weights)
        perturbed[criterion_key] = base_weights[criterion_key] * mult
        ranked = evaluate_mcda(site_summaries, custom_weights=perturbed)
        for rec in ranked:
            ranking_trajectory[rec.site_id].append(rec.rank)

    return SensitivityRun(
        criterion_key=criterion_key,
        weight_multipliers=multipliers,
        ranking_trajectory=ranking_trajectory,
    )
