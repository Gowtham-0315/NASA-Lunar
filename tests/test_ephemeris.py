"""Unit tests for coordinate transformations, local frames, and lunar ephemerides."""

import math
import pytest
from lunar_intelligence.coordinates import (
    LunarSite,
    local_enu,
    angular_direction,
    effective_horizon_dip_deg,
    site_position_body_fixed,
    dot,
    cross,
    norm,
    unit,
)
from lunar_intelligence.ephemeris_engine import (
    compute_lunar_orientation,
    compute_target_geometry,
)
from lunar_intelligence.time_system import datetime_to_jd, parse_utc


def test_vector_algebra():
    v1 = (1.0, 0.0, 0.0)
    v2 = (0.0, 1.0, 0.0)
    assert dot(v1, v2) == 0.0
    assert cross(v1, v2) == (0.0, 0.0, 1.0)
    assert norm((3.0, 4.0, 0.0)) == 5.0
    u = unit((0.0, 10.0, 0.0))
    assert pytest.approx(u[1], 1e-6) == 1.0


def test_local_enu_orthonormality():
    site = LunarSite(latitude_deg=-89.0, longitude_deg=45.0, site_id="TEST_SITE")
    frame = local_enu(site)

    # Check unit vectors
    assert pytest.approx(norm(frame.east), 1e-9) == 1.0
    assert pytest.approx(norm(frame.north), 1e-9) == 1.0
    assert pytest.approx(norm(frame.up), 1e-9) == 1.0

    # Check orthogonality
    assert pytest.approx(dot(frame.east, frame.north), 1e-9) == 0.0
    assert pytest.approx(dot(frame.east, frame.up), 1e-9) == 0.0
    assert pytest.approx(dot(frame.north, frame.up), 1e-9) == 0.0


def test_effective_horizon_dip():
    # 2-meter mast should dip horizon by ~0.087° (5.2 arcmin)
    dip = effective_horizon_dip_deg(2.0)
    assert 0.08 < dip < 0.095

    # 0 mast height
    assert effective_horizon_dip_deg(0.0) == 0.0


def test_lunar_orientation_and_libration():
    dt = parse_utc("2026-12-01T00:00:00Z")
    jd = datetime_to_jd(dt)
    orient = compute_lunar_orientation(jd)

    # Earth-Moon distance should be within ~356,000 to 407,000 km
    assert 3.5e8 < orient.moon_earth_distance_m < 4.1e8

    # Optical + physical libration latitude should be within +/- 7.5°
    assert -7.5 <= orient.sub_earth_lat_deg <= 7.5

    # Libration longitude should be within +/- 9.0°
    assert -9.0 <= orient.sub_earth_lon_deg <= 9.0

    # Sub-solar latitude should be within lunar axial tilt (+/- 1.6°)
    assert -1.6 <= orient.sub_sun_lat_deg <= 1.6


def test_target_geometry_sun_and_earth():
    site = LunarSite(latitude_deg=0.0, longitude_deg=0.0, site_id="CENTER_SITE")
    sun_state = compute_target_geometry("SUN", "2026-12-01T00:00:00Z", site)
    earth_state = compute_target_geometry("EARTH", "2026-12-01T00:00:00Z", site)

    # At (0, 0), Earth is near zenith (elevation > 80°)
    assert earth_state.elevation_deg > 75.0
    assert earth_state.angular_radius_deg > 0.85

    # Solar distance is ~1 AU
    assert 1.4e11 < sun_state.distance_m < 1.6e11
    # Solar angular radius is ~0.267°
    assert 0.25 < sun_state.angular_radius_deg < 0.28
