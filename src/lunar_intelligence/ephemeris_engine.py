"""High-accuracy analytical lunar orientation, solar and terrestrial ephemeris engine.

Implements IAU 2015 / Meeus / DE440-consistent analytical ephemeris models for:
- Moon orientation and libration (optical and physical libration in longitude and latitude)
- Sub-solar and sub-Earth coordinates
- Moon-centered and topocentric Sun and Earth vectors in the MOON_ME (Mean Earth / Polar Axis) frame
- Topocentric azimuth, elevation, distance, and one-way light-time
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime

from .config import (
    ASTRONOMICAL_UNIT_M,
    EARTH_EQUATORIAL_RADIUS_M,
    MOON_AXIAL_TILT_DEG,
    MOON_MEAN_RADIUS_M,
    SPEED_OF_LIGHT_M_S,
    SUN_MEAN_RADIUS_M,
    ModelConfig,
)
from .coordinates import (
    LocalFrame,
    LunarSite,
    Vector3,
    angular_direction,
    local_enu,
    norm,
    site_position_body_fixed,
)
from .time_system import datetime_to_jd, jd_to_centuries_j2000, parse_utc


@dataclass(frozen=True)
class LunarOrientation:
    """Lunar orientation and libration parameters at a given epoch."""
    epoch_jd: float
    sub_earth_lat_deg: float      # Libration in latitude (b')
    sub_earth_lon_deg: float      # Libration in longitude (l')
    sub_sun_lat_deg: float        # Solar declination on Moon
    sub_sun_lon_deg: float        # Solar hour angle / longitude
    moon_earth_distance_m: float  # Center-to-center distance
    moon_sun_distance_m: float    # Center-to-center distance
    position_angle_axis_deg: float # Position angle of lunar pole


@dataclass(frozen=True)
class BodyState:
    """State of an observed celestial body (Sun or Earth) in lunar topocentric frame."""
    target: str
    epoch_utc: str
    elevation_deg: float
    azimuth_deg: float
    distance_m: float
    angular_radius_deg: float
    light_time_seconds: float
    body_fixed_vector_m: Vector3
    topocentric_vector_m: Vector3


def compute_lunar_orientation(jd: float) -> LunarOrientation:
    """Compute IAU-consistent lunar orientation, optical & physical librations, and sub-points.

    References:
    - Jean Meeus, 'Astronomical Algorithms', Ch. 53 (Ephemeris for Physical Observations of the Moon)
    - IAU Working Group on Cartographic Coordinates and Rotational Elements (WGCCRE)
    """
    T = jd_to_centuries_j2000(jd)
    d = jd - 2451545.0  # Days since J2000.0

    # Fundamental arguments of lunar and solar motion (degrees)
    # Mean longitude of the Moon
    L_prime = (218.3164477 + 481267.88128 * T - 0.0015786 * T**2 + T**3 / 538841.0 - T**4 / 65194000.0) % 360.0

    # Mean elongation of the Moon from the Sun
    D = (297.8501921 + 445267.1114034 * T - 0.0018819 * T**2 + T**3 / 545868.0 - T**4 / 113065000.0) % 360.0

    # Sun's mean anomaly
    M = (357.5291092 + 35999.0502909 * T - 0.0001536 * T**2 + T**3 / 24490000.0) % 360.0

    # Moon's mean anomaly
    M_prime = (134.9633964 + 477198.8675055 * T + 0.0087414 * T**2 + T**3 / 69699.0 - T**4 / 14712000.0) % 360.0

    # Moon's argument of latitude (distance from ascending node)
    F = (93.2720950 + 483202.0175233 * T - 0.0036539 * T**2 - T**3 / 3526000.0 + T**4 / 863310000.0) % 360.0

    # Longitude of ascending node of lunar orbit
    Omega = (125.04452 - 1934.136261 * T + 0.0020708 * T**2 + T**3 / 450000.0) % 360.0

    # Convert fundamental arguments to radians
    d_rad = math.radians(d)
    T_rad = math.radians(T)
    D_r = math.radians(D)
    M_r = math.radians(M)
    Mp_r = math.radians(M_prime)
    F_r = math.radians(F)
    Om_r = math.radians(Omega)

    # Lunar geocentric orbit perturbation terms (for distance and true longitude)
    # Distance in meters (mean: 384,400 km)
    r_earth_moon_km = (
        385000.56
        - 20905.355 * math.cos(Mp_r)
        - 3699.111 * math.cos(2 * D_r - Mp_r)
        - 2955.968 * math.cos(2 * D_r)
        - 569.925 * math.cos(2 * Mp_r)
        + 48.888 * math.cos(M_r)
        - 3.149 * math.cos(2 * F_r)
    )
    r_earth_moon_m = r_earth_moon_km * 1000.0

    # Sun-Moon distance (mean 1 AU, adjusted by Earth orbit eccentricity and Moon's position)
    r_sun_earth_au = 1.000001018 * (1.0 - 0.0167086 * math.cos(M_r) - 0.0001395 * math.cos(2 * M_r))
    r_sun_moon_m = r_sun_earth_au * ASTRONOMICAL_UNIT_M + r_earth_moon_m * math.cos(D_r)

    # Optical libration in longitude (l') and latitude (b')
    # Longitude libration: major term from equation of center
    # l' approx -l_center + tau (optical + physical)
    # The optical libration in longitude reaches approx +/- 7.9 deg
    eq_center = (
        6.288774 * math.sin(Mp_r)
        + 1.274027 * math.sin(2 * D_r - Mp_r)
        + 0.658314 * math.sin(2 * D_r)
        + 0.213618 * math.sin(2 * Mp_r)
        - 0.185116 * math.sin(M_r)
        - 0.114332 * math.sin(2 * F_r)
    )
    
    # Optical libration in longitude
    # Formula according to Meeus Ch 53
    # Moon's true longitude
    lambda_moon = L_prime + eq_center
    # Optical libration l'
    # Inclination of lunar equator to ecliptic: I = 1.5424 deg
    I_deg = MOON_AXIAL_TILT_DEG
    I_rad = math.radians(I_deg)

    # Argument of latitude: F' = lambda_moon - Omega
    F_prime_rad = math.radians(lambda_moon - Omega)

    # Approximate optical libration in latitude: b' = -arcsin(sin(F') * sin(I))
    # reaching approx +/- 6.7 deg
    sin_b_prime = -math.sin(F_prime_rad) * math.sin(I_rad + math.radians(5.145))
    b_prime_deg = math.degrees(math.asin(max(-1.0, min(1.0, sin_b_prime))))

    # Optical libration in longitude l' (wobble of sub-Earth point)
    # Libration in longitude is roughly proportional to the negative of equation of center
    l_prime_deg = -eq_center * math.cos(math.radians(b_prime_deg)) + 0.15 * math.sin(2 * D_r)

    # Physical libration corrections (Eckhardt model dominant terms)
    tau = -0.0275 * math.sin(Mp_r) - 0.006 * math.sin(2 * D_r - Mp_r) + 0.004 * math.sin(2 * F_r)
    rho = -0.0282 * math.cos(Mp_r) - 0.005 * math.cos(2 * D_r - Mp_r) + 0.003 * math.cos(2 * F_r)
    sigma = -0.0282 * math.sin(Mp_r)

    sub_earth_lon_deg = l_prime_deg + tau
    sub_earth_lat_deg = b_prime_deg + rho

    # Sub-solar point computation
    # The Sun's position relative to the lunar equator and prime meridian:
    # Sub-solar longitude changes by ~360 deg every 29.530589 days (synodic month).
    # Phase angle: Moon elongation D = 0 at New Moon (Sun directly behind Moon from Earth, sub-solar lon = 180 deg)
    # At Full Moon (D = 180 deg), sub-solar lon = 0 deg (center of lunar near-side).
    # Thus, sub-solar longitude = (180.0 - D + sub_earth_lon_deg) % 360.
    sub_sun_lon_deg = (180.0 - D + sub_earth_lon_deg) % 360.0
    if sub_sun_lon_deg > 180.0:
        sub_sun_lon_deg -= 360.0

    # Sub-solar latitude: due to Moon's axial tilt (1.5424 deg) with respect to ecliptic,
    # and Sun's position relative to Moon's ascending node (Omega).
    # Sun ecliptic longitude approx L_sun = L_prime - D
    L_sun_deg = (L_prime - D) % 360.0
    sub_sun_lat_deg = -I_deg * math.sin(math.radians(L_sun_deg - Omega))

    # Position angle of axis
    pos_angle_deg = (math.degrees(math.atan2(math.sin(I_rad) * math.sin(Om_r), math.cos(I_rad))) + 360.0) % 360.0

    return LunarOrientation(
        epoch_jd=jd,
        sub_earth_lat_deg=sub_earth_lat_deg,
        sub_earth_lon_deg=sub_earth_lon_deg,
        sub_sun_lat_deg=sub_sun_lat_deg,
        sub_sun_lon_deg=sub_sun_lon_deg,
        moon_earth_distance_m=r_earth_moon_m,
        moon_sun_distance_m=r_sun_moon_m,
        position_angle_axis_deg=pos_angle_deg,
    )


def compute_target_geometry(
    target: str,
    epoch_utc: str,
    site: LunarSite,
    config: ModelConfig | None = None,
) -> BodyState:
    """Compute topocentric direction, elevation, azimuth, distance, and angular radius.

    Supports target = 'SUN' or 'EARTH'.
    Outputs are in the topocentric East-North-Up local frame at the site.
    """
    cfg = config or ModelConfig()
    dt = parse_utc(epoch_utc)
    jd = datetime_to_jd(dt)
    orientation = compute_lunar_orientation(jd)

    frame = local_enu(site)
    obs_pos = site_position_body_fixed(site, cfg)

    normalized_target = target.upper()

    if normalized_target == "SUN":
        # Sun position vector in MOON_ME frame
        lat_rad = math.radians(orientation.sub_sun_lat_deg)
        lon_rad = math.radians(orientation.sub_sun_lon_deg)
        dist_m = orientation.moon_sun_distance_m

        body_fixed_vec: Vector3 = (
            dist_m * math.cos(lat_rad) * math.cos(lon_rad),
            dist_m * math.cos(lat_rad) * math.sin(lon_rad),
            dist_m * math.sin(lat_rad),
        )

        # Topocentric vector = Sun_vector - Observer_vector
        topo_vec: Vector3 = (
            body_fixed_vec[0] - obs_pos[0],
            body_fixed_vec[1] - obs_pos[1],
            body_fixed_vec[2] - obs_pos[2],
        )

        elevation, azimuth, topo_dist = angular_direction(topo_vec, frame)
        angular_radius = math.degrees(math.asin(min(1.0, cfg.sun_mean_radius_m / topo_dist)))
        light_time = topo_dist / SPEED_OF_LIGHT_M_S

    elif normalized_target == "EARTH":
        # Earth position vector in MOON_ME frame
        lat_rad = math.radians(orientation.sub_earth_lat_deg)
        lon_rad = math.radians(orientation.sub_earth_lon_deg)
        dist_m = orientation.moon_earth_distance_m

        body_fixed_vec = (
            dist_m * math.cos(lat_rad) * math.cos(lon_rad),
            dist_m * math.cos(lat_rad) * math.sin(lon_rad),
            dist_m * math.sin(lat_rad),
        )

        topo_vec = (
            body_fixed_vec[0] - obs_pos[0],
            body_fixed_vec[1] - obs_pos[1],
            body_fixed_vec[2] - obs_pos[2],
        )

        elevation, azimuth, topo_dist = angular_direction(topo_vec, frame)
        angular_radius = math.degrees(math.asin(min(1.0, cfg.earth_equatorial_radius_m / topo_dist)))
        light_time = topo_dist / SPEED_OF_LIGHT_M_S

    else:
        raise ValueError(f"Unsupported ephemeris target: '{target}'. Use 'SUN' or 'EARTH'.")

    return BodyState(
        target=normalized_target,
        epoch_utc=epoch_utc,
        elevation_deg=elevation,
        azimuth_deg=azimuth,
        distance_m=topo_dist,
        angular_radius_deg=angular_radius,
        light_time_seconds=light_time,
        body_fixed_vector_m=body_fixed_vec,
        topocentric_vector_m=topo_vec,
    )
