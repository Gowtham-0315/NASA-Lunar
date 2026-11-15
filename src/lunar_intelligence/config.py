"""Configuration, physical constants, and default mission parameters."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Any

# Astronomical and physical constants
MOON_MEAN_RADIUS_M: float = 1_737_400.0
MOON_EQUATORIAL_RADIUS_M: float = 1_738_140.0
MOON_POLAR_RADIUS_M: float = 1_735_970.0
SUN_MEAN_RADIUS_M: float = 695_700_000.0
EARTH_EQUATORIAL_RADIUS_M: float = 6_378_137.0
ASTRONOMICAL_UNIT_M: float = 149_597_870_700.0
SPEED_OF_LIGHT_M_S: float = 299_792_458.0
BOLTZMANN_CONSTANT: float = 1.380649e-23  # J/K
SOLAR_CONSTANT_W_M2: float = 1361.0  # Solar irradiance at 1 AU

# Orbital & Rotational dynamics
MOON_AXIAL_TILT_DEG: float = 1.5424  # Relative to ecliptic pole
MOON_ORBITAL_INCLINATION_DEG: float = 5.145
SYNODIC_MONTH_DAYS: float = 29.530589
SIDEREAL_MONTH_DAYS: float = 27.321661

# Deep Space Network (DSN) ground stations
DSN_STATIONS: Dict[str, Dict[str, Any]] = {
    "Goldstone": {
        "name": "Goldstone Deep Space Communications Complex (GDSCC)",
        "latitude_deg": 35.4267,
        "longitude_deg": -116.8900,
        "elevation_m": 1035.0,
        "min_elevation_deg": 6.0,
        "antennas": ["DSS-14 (70m)", "DSS-24 (34m BWG)", "DSS-25 (34m BWG)", "DSS-26 (34m BWG)"]
    },
    "Madrid": {
        "name": "Madrid Deep Space Communications Complex (MDSCC)",
        "latitude_deg": 40.4272,
        "longitude_deg": -4.2500,
        "elevation_m": 780.0,
        "min_elevation_deg": 6.0,
        "antennas": ["DSS-63 (70m)", "DSS-65 (34m HEF)", "DSS-54 (34m BWG)", "DSS-56 (34m BWG)"]
    },
    "Canberra": {
        "name": "Canberra Deep Space Communication Complex (CDSCC)",
        "latitude_deg": -35.4014,
        "longitude_deg": 148.9817,
        "elevation_m": 650.0,
        "min_elevation_deg": 6.0,
        "antennas": ["DSS-43 (70m)", "DSS-34 (34m BWG)", "DSS-35 (34m BWG)", "DSS-36 (34m BWG)"]
    }
}

# RF communication bands
RF_BANDS: Dict[str, Dict[str, Any]] = {
    "S-Band": {
        "frequency_hz": 2.25e9,
        "description": "2.25 GHz Space Operations / DSN S-Band Downlink",
        "lambda_m": SPEED_OF_LIGHT_M_S / 2.25e9,
        "dsn_34m_gt_db_k": 32.5,
        "dsn_70m_gt_db_k": 40.5,
        "atm_loss_nominal_db": 0.05
    },
    "X-Band": {
        "frequency_hz": 8.45e9,
        "description": "8.45 GHz Deep Space Science / DSN X-Band Downlink",
        "lambda_m": SPEED_OF_LIGHT_M_S / 8.45e9,
        "dsn_34m_gt_db_k": 42.0,
        "dsn_70m_gt_db_k": 51.5,
        "atm_loss_nominal_db": 0.12
    },
    "Ka-Band": {
        "frequency_hz": 32.05e9,
        "description": "32.05 GHz High-Throughput / DSN Ka-Band Downlink",
        "lambda_m": SPEED_OF_LIGHT_M_S / 32.05e9,
        "dsn_34m_gt_db_k": 53.5,
        "dsn_70m_gt_db_k": 62.0,
        "atm_loss_nominal_db": 0.40
    }
}

# Canadian Space Agency (ASC-CSA) rover operational constraints
CSA_ROVER_CONSTRAINTS = {
    "max_slope_deg": 15.0,  # Tip-over and mobility boundary for micro-rover
    "min_solar_irradiance_w_m2": 200.0,  # Required for solar array power positive
    "min_sunlit_continuous_hours": 48.0,  # Required for primary volatile prospecting campaign
    "psr_traverse_speed_m_h": 50.0,  # Speed inside Permanently Shadowed Regions
    "min_earth_elevation_deg": 3.0,  # DTE direct teleoperation link
    "gateway_relay_supported": True
}


@dataclass(frozen=True)
class ModelConfig:
    """Configurable parameters for lunar geometry and mission simulation."""
    lunar_fixed_frame: str = "MOON_ME"
    inertial_frame: str = "J2000"
    aberration_correction: str = "LT+S"
    moon_radius_m: float = MOON_MEAN_RADIUS_M
    sun_mean_radius_m: float = SUN_MEAN_RADIUS_M
    earth_equatorial_radius_m: float = EARTH_EQUATORIAL_RADIUS_M
    antenna_mast_height_m: float = 2.0  # Height of lander antenna above surface
    min_earth_elevation_deg: float = 0.0  # Minimum operational elevation
    touchdown_sun_min_deg: float = 5.0  # Optimal lower sun angle for shadow contrast
    touchdown_sun_max_deg: float = 20.0  # Optimal upper sun angle for descent navigation
    weights: Dict[str, float] = field(default_factory=lambda: {
        "illumination": 0.25,
        "earth_los": 0.25,
        "co_visibility": 0.20,
        "slope_safety": 0.15,
        "science_value": 0.15
    })
