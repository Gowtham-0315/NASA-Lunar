"""Scientific interpretability and explainable natural language rationale generator."""

from __future__ import annotations

from typing import Any, Dict, List

from .coordinates import LunarSite
from .landing_evaluator import SiteWindowSummary
from .mcda_engine import ScoredSiteRecord


def generate_site_explanation(
    site: LunarSite,
    summary: SiteWindowSummary,
    score_record: ScoredSiteRecord | None = None,
) -> Dict[str, Any]:
    """Generate detailed, scientifically grounded natural language explanations for a site."""
    points: List[str] = []
    risks: List[str] = []
    strengths: List[str] = []

    # 1. Solar illumination analysis
    if summary.sunlight_fraction >= 0.70:
        strengths.append(
            f"High persistent illumination: Sun above horizon for {summary.sunlight_fraction*100:.1f}% "
            f"({summary.sunlight_duration_hours:.1f} hours) of the mission window. "
            f"Peak continuous sun of {summary.longest_continuous_sunlight_hours:.1f}h provides robust battery recharge."
        )
    elif summary.sunlight_fraction >= 0.40:
        points.append(
            f"Moderate solar availability: {summary.sunlight_fraction*100:.1f}% illumination. "
            f"Requires secondary power storage for max dark duration of {summary.longest_dark_period_hours:.1f} hours."
        )
    else:
        risks.append(
            f"Severe shadow deficit: Only {summary.sunlight_fraction*100:.1f}% sunlight. "
            f"Extended darkness of {summary.longest_dark_period_hours:.1f} hours poses extreme cryo-thermal survival hazards."
        )

    # 2. Earth visibility & DTE communications
    if summary.earth_los_fraction >= 0.90:
        strengths.append(
            f"Continuous direct-to-Earth communication: Earth in line-of-sight {summary.earth_los_fraction*100:.1f}% "
            f"of the time. Mean elevation {summary.max_earth_elevation_deg:.1f}° avoids terrain multipath interference."
        )
    elif summary.earth_los_fraction >= 0.50:
        points.append(
            f"Intermittent Earth contact: {summary.earth_los_fraction*100:.1f}% line-of-sight. "
            f"Libration and topography induce comms blackouts up to {summary.longest_comms_blackout_hours:.1f} hours."
        )
    else:
        risks.append(
            f"Severe communications blackout: Earth visible only {summary.earth_los_fraction*100:.1f}% of mission. "
            f"Autonomous rover operations or Lunar Gateway / relay satellite support required."
        )

    # 3. Terrain & Slope hazards
    if site.mean_slope_deg <= 5.0:
        strengths.append(
            f"Benign local slope: Mean terrain gradient is {site.mean_slope_deg:.1f}°, well within standard "
            f"lander descent envelope (< 10°) and Canadian rover mobility limits (< 15°)."
        )
    elif site.mean_slope_deg <= 10.0:
        points.append(
            f"Manageable terrain relief: Mean slope of {site.mean_slope_deg:.1f}° with roughness score {site.roughness_score:.2f}. "
            f"Terrain relative navigation (TRN) required to target local flat terrace."
        )
    else:
        risks.append(
            f"Hazardous landing slopes: Regional slope of {site.mean_slope_deg:.1f}° exceeds nominal landing safety margins. "
            f"Elevated risk of lander tip-over or rover wheel immobilization."
        )

    # 4. Landing windows
    num_windows = len(summary.touchdown_windows)
    if num_windows > 0:
        strengths.append(
            f"Found {num_windows} viable touchdown window(s) totaling {summary.total_landing_window_hours:.1f} hours. "
            f"Solar elevation remains in optimal 5°–20° range with active DSN telemetry support."
        )
    else:
        risks.append(
            "No viable touchdown windows identified where solar elevation is between 5°–20° with simultaneous "
            "safe Earth elevation (>= 5°) and active DSN line-of-sight."
        )

    # 5. Scientific priority
    if site.scientific_priority >= 0.90:
        strengths.append(
            f"Top-tier volatile prospecting priority ({site.scientific_priority*100:.0f}%). "
            f"Directly adjacent to permanently shadowed cold-traps holding suspected water ice deposits."
        )

    # Rank interpretation
    rank_explanation = ""
    if score_record:
        rank_explanation = (
            f"Ranked #{score_record.rank} among evaluated candidate sites with an overall WSM score of "
            f"{score_record.wsm_score:.1f}/100 and TOPSIS relative closeness of {score_record.topsis_score:.1f}%. "
            f"{'It lies on the Pareto-optimal trade-off frontier.' if score_record.is_pareto_optimal else 'It is dominated on the Pareto frontier by other candidate sites.'}"
        )

    return {
        "site_id": site.site_id,
        "site_name": site.name,
        "region": site.region,
        "rank_explanation": rank_explanation,
        "key_strengths": strengths,
        "key_risks": risks,
        "operational_considerations": points,
        "assumptions": [
            "Body-fixed coordinate frame: MOON_ME (Mean Earth / Polar Axis, DE440-aligned)",
            "Sun disc model: Finite disk with 0.267° angular radius and circular segment partial penumbra",
            "Antenna elevation: 2.0 m mast height above local ground level",
            "DSN network: Goldstone, Madrid, and Canberra stations with 6.0° local elevation mask",
            "Landing criteria: Solar elevation between 5.0° and 20.0°, Earth elevation >= 5.0°, and unobstructed line-of-sight",
            "Topographic DEM: LOLA / SLDEM2015 360-degree synthesized horizon mask obstruction profile"
        ],
    }
