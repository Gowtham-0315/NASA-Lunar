"""Earth visibility intelligence module: topocentric elevation, azimuth, DTE LOS, and mast height advantages."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional

from .config import ModelConfig
from .coordinates import LunarSite, effective_horizon_dip_deg
from .ephemeris_engine import compute_target_geometry


@dataclass(frozen=True)
class EarthState:
    """Complete topocentric Earth observation and direct-to-Earth (DTE) state."""
    epoch_utc: str
    elevation_deg: float
    azimuth_deg: float
    distance_m: float
    angular_radius_deg: float
    light_time_seconds: float
    
    # Visibility conditions
    center_above_horizon: bool
    upper_limb_above_horizon: bool
    full_disc_above_horizon: bool
    disc_visible_fraction: float
    
    # Antenna mast advantage
    antenna_mast_height_m: float
    horizon_dip_deg: float
    effective_elevation_deg: float  # elevation + horizon_dip
    dte_los_available: bool         # effective_elevation >= min_elevation_deg
    
    # Regional classification
    visibility_regime: str  # 'PERMANENT_DIRECT_VIEW', 'LIBRATION_OCCULTED_LIMB', 'PERMANENT_FAR_SIDE_OCCULTATION'


def calculate_earth_state(
    site: LunarSite,
    epoch_utc: str,
    antenna_mast_height_m: float = 2.0,
    min_elevation_deg: float = 0.0,
    config: Optional[ModelConfig] = None,
) -> EarthState:
    """Calculate topocentric Earth position, antenna mast elevation gain, and DTE LOS."""
    cfg = config or ModelConfig()
    body_state = compute_target_geometry("EARTH", epoch_utc, site, cfg)

    el = body_state.elevation_deg
    az = body_state.azimuth_deg
    r_deg = body_state.angular_radius_deg
    dist_m = body_state.distance_m
    light_time = body_state.light_time_seconds

    # Dip angle due to antenna mast height
    dip_deg = effective_horizon_dip_deg(antenna_mast_height_m, cfg.moon_radius_m)
    effective_el = el + dip_deg

    center_above = effective_el > 0.0
    upper_limb_above = (effective_el + r_deg) > 0.0
    full_disc_above = (effective_el - r_deg) > 0.0

    # Disc fraction visible
    if effective_el <= -r_deg:
        disc_frac = 0.0
    elif effective_el >= r_deg:
        disc_frac = 1.0
    else:
        ratio = max(-1.0, min(1.0, -effective_el / r_deg))
        theta = 2.0 * math.acos(ratio)
        disc_frac = max(0.0, min(1.0, (theta - math.sin(theta)) / (2.0 * math.pi)))

    # Direct to Earth line-of-sight meeting minimum threshold
    dte_los = effective_el >= min_elevation_deg and upper_limb_above

    # Classify visibility regime
    # Near-side central longitudes/latitudes have Earth high in sky
    # Edge longitudes (> ~80 deg) or near poles experience libration dips
    abs_lat = abs(site.latitude_deg)
    abs_lon = abs(site.signed_longitude_deg)

    if abs_lon > 98.0:
        regime = "PERMANENT_FAR_SIDE_OCCULTATION"
    elif abs_lon > 75.0 or abs_lat > 75.0:
        regime = "LIBRATION_OCCULTED_LIMB"
    else:
        regime = "PERMANENT_DIRECT_VIEW"

    return EarthState(
        epoch_utc=epoch_utc,
        elevation_deg=round(el, 4),
        azimuth_deg=round(az, 4),
        distance_m=dist_m,
        angular_radius_deg=round(r_deg, 4),
        light_time_seconds=round(light_time, 4),
        center_above_horizon=center_above,
        upper_limb_above_horizon=upper_limb_above,
        full_disc_above_horizon=full_disc_above,
        disc_visible_fraction=round(disc_frac, 4),
        antenna_mast_height_m=antenna_mast_height_m,
        horizon_dip_deg=round(dip_deg, 4),
        effective_elevation_deg=round(effective_el, 4),
        dte_los_available=dte_los,
        visibility_regime=regime,
    )
