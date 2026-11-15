"""Unit tests for solar intelligence, disc fractions, and flux calculations."""

import pytest
from lunar_intelligence.coordinates import LunarSite
from lunar_intelligence.solar_intelligence import (
    calculate_disc_fraction,
    calculate_solar_state,
)


def test_disc_fraction_geometry():
    radius = 0.267
    # Fully above horizon
    assert calculate_disc_fraction(1.0, radius) == 1.0
    # Fully below horizon
    assert calculate_disc_fraction(-1.0, radius) == 0.0
    # Exactly at horizon (center elevation = 0)
    assert pytest.approx(calculate_disc_fraction(0.0, radius), 1e-4) == 0.5
    # Upper limb touching
    assert 0.0 < calculate_disc_fraction(-0.1, radius) < 0.5


def test_solar_state_polar_site():
    site = LunarSite(latitude_deg=-89.6, longitude_deg=129.8, site_id="SHACKLETON_RIM")
    state = calculate_solar_state(site, "2026-12-01T00:00:00Z")

    assert -90.0 <= state.elevation_deg <= 90.0
    assert 0.0 <= state.azimuth_deg <= 360.0
    assert 0.0 <= state.disc_illuminated_fraction <= 1.0
    assert state.incident_flux_horizontal_w_m2 >= 0.0
