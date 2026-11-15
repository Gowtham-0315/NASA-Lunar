"""Solar intelligence module: elevation, azimuth, disc visibility, partial illumination, and solar flux."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional

from .config import SOLAR_CONSTANT_W_M2, ModelConfig
from .coordinates import LunarSite
from .ephemeris_engine import compute_target_geometry


@dataclass(frozen=True)
class SolarState:
    """Complete topocentric solar illumination state at a specific epoch."""
    epoch_utc: str
    elevation_deg: float
    azimuth_deg: float
    distance_m: float
    angular_radius_deg: float
    
    # Visibility conditions
    center_above_horizon: bool
    upper_limb_above_horizon: bool  # Civil sunrise/sunset threshold (-0.267°)
    full_disc_above_horizon: bool
    disc_illuminated_fraction: float  # 0.0 (full dark) to 1.0 (full sun)
    
    # Incident solar power
    incident_flux_horizontal_w_m2: float
    incident_flux_vertical_tracker_w_m2: float
    solar_constant_w_m2: float = SOLAR_CONSTANT_W_M2


def calculate_disc_fraction(elevation_deg: float, angular_radius_deg: float) -> float:
    """Calculate visible fraction of the solar disk above a flat horizon.

    Uses the exact circular segment area formula:
    - Elevation <= -angular_radius -> 0.0 (below horizon)
    - Elevation >= +angular_radius -> 1.0 (fully above horizon)
    - In between -> partial disk (penumbra)
    """
    if angular_radius_deg <= 0:
        return 1.0 if elevation_deg > 0 else 0.0

    if elevation_deg <= -angular_radius_deg:
        return 0.0
    if elevation_deg >= angular_radius_deg:
        return 1.0

    # h is distance from center of disk to horizon line: h = elevation_deg
    # fraction of disk above horizon:
    # theta = 2 * acos(-elevation_deg / angular_radius_deg)
    # Area = 0.5 * R^2 * (theta - sin(theta))
    # Fraction = Area / (pi * R^2)
    ratio = max(-1.0, min(1.0, -elevation_deg / angular_radius_deg))
    theta = 2.0 * math.acos(ratio)
    fraction = (theta - math.sin(theta)) / (2.0 * math.pi)
    return max(0.0, min(1.0, fraction))


def calculate_solar_state(
    site: LunarSite,
    epoch_utc: str,
    config: Optional[ModelConfig] = None,
) -> SolarState:
    """Calculate topocentric solar position, disc geometry, and incident irradiance."""
    cfg = config or ModelConfig()
    body_state = compute_target_geometry("SUN", epoch_utc, site, cfg)

    el = body_state.elevation_deg
    az = body_state.azimuth_deg
    r_deg = body_state.angular_radius_deg
    dist_m = body_state.distance_m

    center_above = el > 0.0
    upper_limb_above = (el + r_deg) > 0.0
    full_disc_above = (el - r_deg) > 0.0

    disc_fraction = calculate_disc_fraction(el, r_deg)

    # Solar flux calculations
    # Adjust solar constant for varying Sun-Moon distance
    dist_au = dist_m / 149597870700.0
    flux_at_distance = SOLAR_CONSTANT_W_M2 / (dist_au ** 2)

    # Flux on horizontal lunar surface: F_horiz = F0 * sin(el) * fraction
    if el > -r_deg and disc_fraction > 0:
        sin_el = max(0.0, math.sin(math.radians(max(0.0, el))))
        # Even during grazing upper limb, partial flux reaches the surface
        effective_sin = max(0.01 * disc_fraction, sin_el)
        flux_horiz = flux_at_distance * effective_sin * disc_fraction
        # Flux on a vertical solar panel oriented towards the Sun (optimal for polar low-sun conditions)
        cos_el = math.cos(math.radians(max(-89.0, min(89.0, el))))
        flux_vert = flux_at_distance * cos_el * disc_fraction
    else:
        flux_horiz = 0.0
        flux_vert = 0.0

    return SolarState(
        epoch_utc=epoch_utc,
        elevation_deg=round(el, 4),
        azimuth_deg=round(az, 4),
        distance_m=dist_m,
        angular_radius_deg=round(r_deg, 4),
        center_above_horizon=center_above,
        upper_limb_above_horizon=upper_limb_above,
        full_disc_above_horizon=full_disc_above,
        disc_illuminated_fraction=round(disc_fraction, 4),
        incident_flux_horizontal_w_m2=round(flux_horiz, 2),
        incident_flux_vertical_tracker_w_m2=round(flux_vert, 2),
        solar_constant_w_m2=round(flux_at_distance, 2),
    )
