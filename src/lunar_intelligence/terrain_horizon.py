"""Terrain elevation models, 360-degree horizon masks, and shadow occlusion."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, List, Tuple

from .coordinates import LunarSite


@dataclass(frozen=True)
class HorizonMask:
    """A 360-degree topocentric horizon elevation profile for a lunar site."""
    site_id: str
    azimuths_deg: List[float]
    horizon_elevations_deg: List[float]
    max_obstruction_deg: float
    min_obstruction_deg: float
    mean_obstruction_deg: float


@dataclass(frozen=True)
class TerrainOcclusionResult:
    """Evaluation of whether a celestial target is occluded by local topography."""
    azimuth_deg: float
    target_elevation_deg: float
    horizon_elevation_deg: float
    is_occluded_by_terrain: bool
    clearance_above_horizon_deg: float
    partial_terrain_factor: float  # 0.0 (fully blocked) to 1.0 (fully clear)


# Topographic profiles based on LOLA / SLDEM2015 data for key sites
# Profiles model crater rims, central peaks, and regional massifs
SITE_TERRAIN_SIGNATURES: Dict[str, Dict[str, float]] = {
    # South Pole Artemis III sites
    "SHACKLETON_RIM": {
        "base_el": 1.8,
        "rim_azimuth": 125.0,
        "rim_peak_el": 6.8,
        "ridge_azimuth": 310.0,
        "ridge_peak_el": 4.2,
        "slope": 7.2,
        "roughness": 0.42,
    },
    "MALAPERT_MOUNTAIN": {
        "base_el": 0.5,
        "rim_azimuth": 210.0,
        "rim_peak_el": 3.8,
        "ridge_azimuth": 45.0,
        "ridge_peak_el": 2.2,
        "slope": 4.8,
        "roughness": 0.28,
    },
    "CONNECTING_RIDGE": {
        "base_el": 1.2,
        "rim_azimuth": 90.0,
        "rim_peak_el": 4.6,
        "ridge_azimuth": 270.0,
        "ridge_peak_el": 3.1,
        "slope": 5.4,
        "roughness": 0.31,
    },
    "NOBILE_RIM_1": {
        "base_el": 1.0,
        "rim_azimuth": 180.0,
        "rim_peak_el": 5.2,
        "ridge_azimuth": 350.0,
        "ridge_peak_el": 2.8,
        "slope": 6.1,
        "roughness": 0.35,
    },
    "HAWORTH_CRATER_RIM": {
        "base_el": 1.5,
        "rim_azimuth": 140.0,
        "rim_peak_el": 6.2,
        "ridge_azimuth": 320.0,
        "ridge_peak_el": 3.9,
        "slope": 8.5,
        "roughness": 0.46,
    },
    "PEAK_NEAR_SHACKLETON": {
        "base_el": 0.8,
        "rim_azimuth": 110.0,
        "rim_peak_el": 4.1,
        "ridge_azimuth": 290.0,
        "ridge_peak_el": 2.6,
        "slope": 5.2,
        "roughness": 0.29,
    },
    "CHANDRAYAAN3_SHIV_SHAKTI": {
        "base_el": 0.4,
        "rim_azimuth": 160.0,
        "rim_peak_el": 2.4,
        "ridge_azimuth": 340.0,
        "ridge_peak_el": 1.6,
        "slope": 4.2,
        "roughness": 0.22,
    },
    "APOLLO11_MARE_TRANQUILLITATIS": {
        "base_el": 0.1,
        "rim_azimuth": 0.0,
        "rim_peak_el": 0.4,
        "ridge_azimuth": 180.0,
        "ridge_peak_el": 0.3,
        "slope": 1.5,
        "roughness": 0.10,
    },
}


def compute_horizon_elevation(site: LunarSite, azimuth_deg: float) -> float:
    """Compute terrain elevation obstruction angle (in degrees) for a given azimuth."""
    az = azimuth_deg % 360.0
    sig = SITE_TERRAIN_SIGNATURES.get(site.site_id)

    if sig:
        base = sig["base_el"]
        # Rim component
        d_az1 = (az - sig["rim_azimuth"] + 180.0) % 360.0 - 180.0
        rim_peak = sig["rim_peak_el"] - base
        rim_contrib = rim_peak * math.exp(-((d_az1 / 45.0) ** 2))

        # Ridge component
        d_az2 = (az - sig["ridge_azimuth"] + 180.0) % 360.0 - 180.0
        ridge_peak = sig["ridge_peak_el"] - base
        ridge_contrib = ridge_peak * math.exp(-((d_az2 / 55.0) ** 2))

        # Modest micro-relief ripple
        micro = 0.2 * math.sin(math.radians(az * 4.0))

        h_el = base + rim_contrib + ridge_contrib + micro
        return max(0.0, h_el)

    # Generic polar or equatorial fallback
    if abs(site.latitude_deg) > 75.0:
        # Polar regional terrain typically has rims up to 3-5 deg
        h_el = 1.5 + 2.0 * math.sin(math.radians(az + 30.0)) ** 2
    else:
        # Typical mare/highland fallback
        h_el = 0.3 + 0.4 * math.sin(math.radians(az * 2.0)) ** 2

    return max(0.0, h_el)


def generate_horizon_mask(site: LunarSite, num_azimuths: int = 72) -> HorizonMask:
    """Generate a discrete 360-degree horizon profile for plotting and fast lookups."""
    step = 360.0 / num_azimuths
    azimuths = [i * step for i in range(num_azimuths)]
    elevations = [round(compute_horizon_elevation(site, az), 3) for az in azimuths]

    return HorizonMask(
        site_id=site.site_id,
        azimuths_deg=azimuths,
        horizon_elevations_deg=elevations,
        max_obstruction_deg=round(max(elevations), 3),
        min_obstruction_deg=round(min(elevations), 3),
        mean_obstruction_deg=round(sum(elevations) / len(elevations), 3),
    )


def evaluate_terrain_occlusion(
    site: LunarSite,
    target_elevation_deg: float,
    target_azimuth_deg: float,
    target_angular_radius_deg: float,
) -> TerrainOcclusionResult:
    """Evaluate whether local topography occludes the celestial body."""
    h_el = compute_horizon_elevation(site, target_azimuth_deg)
    clearance = target_elevation_deg - h_el

    r = target_angular_radius_deg
    if clearance >= r:
        # Full disk is above terrain
        occluded = False
        factor = 1.0
    elif clearance <= -r:
        # Full disk is hidden behind terrain
        occluded = True
        factor = 0.0
    else:
        # Partial disc visible above crater rim / mountain
        ratio = max(-1.0, min(1.0, -clearance / r))
        theta = 2.0 * math.acos(ratio)
        factor = max(0.0, min(1.0, (theta - math.sin(theta)) / (2.0 * math.pi)))
        occluded = factor < 0.1

    return TerrainOcclusionResult(
        azimuth_deg=round(target_azimuth_deg, 2),
        target_elevation_deg=round(target_elevation_deg, 3),
        horizon_elevation_deg=round(h_el, 3),
        is_occluded_by_terrain=occluded,
        clearance_above_horizon_deg=round(clearance, 3),
        partial_terrain_factor=round(factor, 3),
    )
