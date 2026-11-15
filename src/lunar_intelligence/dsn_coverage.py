"""Deep Space Network (DSN) ground station tracking and contact scheduler."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, List, Optional

from .config import DSN_STATIONS, EARTH_EQUATORIAL_RADIUS_M
from .ephemeris_engine import compute_lunar_orientation
from .time_system import datetime_to_jd, parse_utc


@dataclass(frozen=True)
class StationElevation:
    """Elevation and contact status for an individual Earth ground station."""
    station_key: str
    station_name: str
    elevation_deg: float
    min_elevation_deg: float
    is_in_contact: bool
    azimuth_deg: float


@dataclass(frozen=True)
class DsnCoverageState:
    """Consolidated Deep Space Network visibility status at a specific epoch."""
    epoch_utc: str
    active_stations: List[str]
    has_dsn_contact: bool
    station_details: Dict[str, StationElevation]
    primary_station: Optional[str]
    handover_in_progress: bool


def calculate_gmst_deg(jd: float) -> float:
    """Compute Greenwich Mean Sidereal Time (GMST) in degrees."""
    d = jd - 2451545.0
    gmst = (280.46061837 + 360.98564736629 * d) % 360.0
    return gmst


def calculate_moon_ra_dec(jd: float) -> tuple[float, float]:
    """Compute geocentric Right Ascension and Declination of the Moon (in degrees)."""
    T = (jd - 2451545.0) / 36525.0
    # Mean arguments
    L_prime = (218.3164477 + 481267.88128 * T) % 360.0
    M_prime = (134.9633964 + 477198.8675 * T) % 360.0
    F = (93.2720950 + 483202.0175 * T) % 360.0
    D = (297.8501921 + 445267.1114 * T) % 360.0

    Mp_r = math.radians(M_prime)
    F_r = math.radians(F)
    D_r = math.radians(D)

    # Ecliptic longitude and latitude
    ecl_lon = L_prime + 6.289 * math.sin(Mp_r) + 1.274 * math.sin(2 * D_r - Mp_r) + 0.658 * math.sin(2 * D_r)
    ecl_lat = 5.128 * math.sin(F_r) + 0.280 * math.sin(Mp_r + F_r)

    # Obliquity of ecliptic
    eps = math.radians(23.439291 - 0.0130042 * T)

    lon_r = math.radians(ecl_lon)
    lat_r = math.radians(ecl_lat)

    # Convert ecliptic to equatorial (RA, Dec)
    sin_dec = math.sin(lat_r) * math.cos(eps) + math.cos(lat_r) * math.sin(eps) * math.sin(lon_r)
    dec = math.degrees(math.asin(max(-1.0, min(1.0, sin_dec))))

    y = math.sin(lon_r) * math.cos(eps) - math.tan(lat_r) * math.sin(eps)
    x = math.cos(lon_r)
    ra = math.degrees(math.atan2(y, x)) % 360.0

    return ra, dec


def calculate_dsn_coverage(epoch_utc: str) -> DsnCoverageState:
    """Calculate Moon visibility from Goldstone, Madrid, and Canberra DSN stations."""
    dt = parse_utc(epoch_utc)
    jd = datetime_to_jd(dt)
    gmst = calculate_gmst_deg(jd)
    ra_moon, dec_moon = calculate_moon_ra_dec(jd)
    orientation = compute_lunar_orientation(jd)
    dist_em_m = orientation.moon_earth_distance_m

    station_results: Dict[str, StationElevation] = {}
    active_keys: List[str] = []

    for key, info in DSN_STATIONS.items():
        lat_rad = math.radians(info["latitude_deg"])
        lon_deg = info["longitude_deg"]
        min_el = info.get("min_elevation_deg", 6.0)

        # Local Sidereal Time
        lst_deg = (gmst + lon_deg) % 360.0
        ha_deg = (lst_deg - ra_moon) % 360.0
        if ha_deg > 180.0:
            ha_deg -= 360.0
        ha_rad = math.radians(ha_deg)
        dec_rad = math.radians(dec_moon)

        # Geocentric elevation
        sin_el = math.sin(lat_rad) * math.sin(dec_rad) + math.cos(lat_rad) * math.cos(dec_rad) * math.cos(ha_rad)
        geocentric_el = math.degrees(math.asin(max(-1.0, min(1.0, sin_el))))

        # Topocentric parallax correction
        # Moon parallax pi = asin(R_E / distance)
        pi_rad = math.asin(EARTH_EQUATORIAL_RADIUS_M / dist_em_m)
        topo_el = geocentric_el - math.degrees(pi_rad * math.cos(math.radians(max(0.0, geocentric_el))))

        # Azimuth from station
        y = -math.sin(ha_rad)
        x = math.tan(dec_rad) * math.cos(lat_rad) - math.sin(lat_rad) * math.cos(ha_rad)
        az_deg = (math.degrees(math.atan2(y, x)) + 360.0) % 360.0

        is_contact = topo_el >= min_el
        if is_contact:
            active_keys.append(key)

        station_results[key] = StationElevation(
            station_key=key,
            station_name=info["name"],
            elevation_deg=round(topo_el, 2),
            min_elevation_deg=min_el,
            is_in_contact=is_contact,
            azimuth_deg=round(az_deg, 2),
        )

    has_contact = len(active_keys) > 0
    primary = active_keys[0] if active_keys else None
    handover = len(active_keys) > 1

    return DsnCoverageState(
        epoch_utc=epoch_utc,
        active_stations=active_keys,
        has_dsn_contact=has_contact,
        station_details=station_results,
        primary_station=primary,
        handover_in_progress=handover,
    )
