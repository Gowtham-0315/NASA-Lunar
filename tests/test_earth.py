"""Unit tests for Earth visibility, DTE LOS, antenna mast advantage, and libration regimes."""

import pytest
from lunar_intelligence.coordinates import LunarSite
from lunar_intelligence.earth_intelligence import calculate_earth_state


def test_near_side_zenith_view():
    apollo11 = LunarSite(latitude_deg=0.674, longitude_deg=23.473, site_id="APOLLO11")
    state = calculate_earth_state(apollo11, "2026-12-01T00:00:00Z")

    assert state.visibility_regime == "PERMANENT_DIRECT_VIEW"
    assert state.center_above_horizon is True
    assert state.dte_los_available is True
    assert state.elevation_deg > 50.0  # High in sky


def test_far_side_permanent_occlusion():
    change4 = LunarSite(latitude_deg=-45.45, longitude_deg=177.59, site_id="CHANGE4")
    state = calculate_earth_state(change4, "2026-12-01T00:00:00Z")

    assert state.visibility_regime == "PERMANENT_FAR_SIDE_OCCULTATION"
    assert state.dte_los_available is False
    assert state.center_above_horizon is False


def test_antenna_mast_gain():
    site = LunarSite(latitude_deg=-89.0, longitude_deg=0.0, site_id="POLAR_TEST")
    state_0m = calculate_earth_state(site, "2026-12-01T00:00:00Z", antenna_mast_height_m=0.0)
    state_3m = calculate_earth_state(site, "2026-12-01T00:00:00Z", antenna_mast_height_m=3.0)

    # 3m mast should provide ~0.106° dip benefit
    assert state_3m.effective_elevation_deg > state_0m.effective_elevation_deg
    assert state_3m.horizon_dip_deg > 0.08
