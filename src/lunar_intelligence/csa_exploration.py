"""Canadian Space Agency (ASC-CSA) Moon Exploration Module.

Covers Canadian lunar exploration initiatives:
- Canadian Lunar Rover (Canadensys / NASA CLPS polar rover)
- Canadarm3 on the Lunar Gateway space station
- Permanently Shadowed Region (PSR) volatile and water ice prospecting
- Canadian mission constraint verification and scoring
Official Resource: https://www.asc-csa.gc.ca/eng/astronomy/moon-exploration/
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

from .config import CSA_ROVER_CONSTRAINTS
from .coordinates import LunarSite


@dataclass(frozen=True)
class CsaRoverPayload:
    """Science or navigation payload aboard the Canadian Lunar Rover."""
    name: str
    instrument_type: str
    target_observable: str
    lead_institution: str
    description: str


@dataclass(frozen=True)
class CsaMissionCompliance:
    """Evaluation of a candidate landing site against Canadian rover constraints."""
    site_id: str
    is_compliant: bool
    slope_compliant: bool
    slope_deg: float
    max_slope_limit_deg: float
    sunlight_compliant: bool
    continuous_lit_hours: float
    min_lit_hours_required: float
    solar_flux_compliant: bool
    max_flux_w_m2: float
    min_flux_required: float
    earth_comms_compliant: bool
    min_earth_el_deg: float
    psr_access_rating: str  # 'EXCELLENT', 'GOOD', 'MODERATE', 'POOR'
    scientific_alignment_score: float  # 0 to 100
    compliance_summary: str
    recommendations: List[str]


# Key Canadian Science & Exploration Payloads
CSA_ROVER_PAYLOADS: List[CsaRoverPayload] = [
    CsaRoverPayload(
        name="Lunar Hydrogen Close-Up Imager (LHCI)",
        instrument_type="Active Neutron Spectrometer & Close-Up Imager",
        target_observable="Water Ice & Volatile Hydrogen in Regolith",
        lead_institution="Canadian Space Agency / University of Winnipeg",
        description="Detects subsurface hydrogen atoms down to 1m depth to locate water ice reserves in polar cold traps.",
    ),
    CsaRoverPayload(
        name="Canadian Lunar 360 Panoramic NavCam",
        instrument_type="Stereo Multispectral Navigation Imager",
        target_observable="Terrain Relief, Boulders & Wheel Slip",
        lead_institution="Canadensys Aerospace (Bolton, Ontario)",
        description="AI-guided autonomous navigation and hazard avoidance system capable of operating in low-angle polar lighting.",
    ),
    CsaRoverPayload(
        name="Deep Tech Volatiles Analyzer (DTVA)",
        instrument_type="Thermal Desorption Mass Spectrometer",
        target_observable="CO2, Methane, Ammonia, Organics",
        lead_institution="McGill University / Western University",
        description="Heats extracted regolith samples to quantify trapped volatile compounds essential for future ISRU life support.",
    ),
    CsaRoverPayload(
        name="Canadian Regolith Radiation Sensor (CRRS)",
        instrument_type="Solid-State Micro-Dosimeter",
        target_observable="Cosmic Rays & Solar Particle Events",
        lead_institution="Bubble Technology Industries (Chalk River, ON)",
        description="Monitors the polar radiation environment to validate astronaut shielding for upcoming Artemis missions.",
    ),
]

# Gateway Canadarm3 System Specifications
CANADARM3_OVERVIEW = {
    "system_name": "Canadarm3 Robotic System",
    "host_platform": "NASA Lunar Gateway (Near Rectilinear Halo Orbit - NRHO)",
    "components": [
        "8.5-metre Large Arm (large-scale cargo and visiting vehicle docking)",
        "Dexterous Small Arm (fine scientific tool and payload handling)",
        "Autonomous Ground Control Software (Saint-Hubert, Quebec mission operations)"
    ],
    "orbital_period_days": 6.5,
    "perilune_altitude_km": 1500,  # Over lunar North Pole
    "apolune_altitude_km": 70000,  # Over lunar South Pole (ideal polar line-of-sight relay)
    "polar_relay_capability": "Provides 2 to 4 days of continuous high-elevation communication relay to South Pole rovers when Earth is occluded by crater rims.",
    "scientific_role": "Autonomous maintenance, external science inspection, and sample transfer from lunar surface ascent modules."
}


def evaluate_csa_compliance(
    site: LunarSite,
    mean_slope_deg: float,
    continuous_lit_hours: float,
    max_flux_w_m2: float,
    min_earth_el_deg: float,
) -> CsaMissionCompliance:
    """Evaluate candidate landing site against Canadian Lunar Rover constraints."""
    max_slope = CSA_ROVER_CONSTRAINTS["max_slope_deg"]
    min_lit_hrs = CSA_ROVER_CONSTRAINTS["min_sunlit_continuous_hours"]
    min_flux = CSA_ROVER_CONSTRAINTS["min_solar_irradiance_w_m2"]
    min_earth_el = CSA_ROVER_CONSTRAINTS["min_earth_elevation_deg"]

    slope_ok = mean_slope_deg <= max_slope
    sunlight_ok = continuous_lit_hours >= min_lit_hrs
    flux_ok = max_flux_w_m2 >= min_flux
    comms_ok = min_earth_el_deg >= min_earth_el

    # PSR accessibility rating (South Pole sites close to rims are prime)
    if abs(site.latitude_deg) >= 88.0:
        psr_rating = "EXCELLENT"
        sci_base = 95.0
    elif abs(site.latitude_deg) >= 80.0:
        psr_rating = "GOOD"
        sci_base = 82.0
    else:
        psr_rating = "POOR"
        sci_base = 40.0

    # Overall compliance
    is_compliant = slope_ok and sunlight_ok and comms_ok

    recommendations: List[str] = []
    if not slope_ok:
        recommendations.append(
            f"Mean slope ({mean_slope_deg:.1f}°) exceeds Canadian micro-rover 15° limit; target alternate flat ridge."
        )
    if not sunlight_ok:
        recommendations.append(
            f"Continuous sunlight ({continuous_lit_hours:.1f}h) is below 48h science prospecting threshold; plan battery conservation."
        )
    if not comms_ok:
        recommendations.append(
            "Direct Earth elevation is near or below horizon; schedule operations during Canadarm3/Gateway NRHO relay passes."
        )
    if psr_rating == "EXCELLENT":
        recommendations.append(
            "Optimal location for Canadian Lunar Hydrogen Close-Up Imager (LHCI) volatile prospecting within adjacent cold traps."
        )

    # Scientific alignment score (0 - 100)
    score = sci_base
    if not slope_ok:
        score -= 25.0
    if not sunlight_ok:
        score -= 15.0
    if not comms_ok:
        score -= 10.0
    score = max(10.0, min(100.0, score))

    summary = (
        f"Site {site.site_id} is {'FULLY COMPLIANT' if is_compliant else 'CONDITIONALLY VIABLE'} "
        f"for the Canadian Lunar Rover. Scientific alignment: {score:.1f}/100 ({psr_rating} PSR access)."
    )

    return CsaMissionCompliance(
        site_id=site.site_id,
        is_compliant=is_compliant,
        slope_compliant=slope_ok,
        slope_deg=mean_slope_deg,
        max_slope_limit_deg=max_slope,
        sunlight_compliant=sunlight_ok,
        continuous_lit_hours=continuous_lit_hours,
        min_lit_hours_required=min_lit_hrs,
        solar_flux_compliant=flux_ok,
        max_flux_w_m2=max_flux_w_m2,
        min_flux_required=min_flux,
        earth_comms_compliant=comms_ok,
        min_earth_el_deg=min_earth_el_deg,
        psr_access_rating=psr_rating,
        scientific_alignment_score=score,
        compliance_summary=summary,
        recommendations=recommendations,
    )
