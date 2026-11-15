"""Unit tests for Deep Space Network tracking and RF downlink budget calculator."""

import pytest
from lunar_intelligence.dsn_coverage import calculate_dsn_coverage
from lunar_intelligence.link_budget import calculate_dish_gain_dbi, calculate_link_budget


def test_dsn_coverage():
    epoch = "2026-12-01T12:00:00Z"
    coverage = calculate_dsn_coverage(epoch)

    # 3 stations: Goldstone, Madrid, Canberra
    assert len(coverage.station_details) == 3
    # At any given time, at least one DSN station should have elevation > 6° for lunar tracking
    assert coverage.has_dsn_contact is True
    assert len(coverage.active_stations) >= 1


def test_dish_gain_calculation():
    # 0.5m dish at X-band (8.45 GHz): Gain should be ~30 dBi
    gain = calculate_dish_gain_dbi(0.5, 8.45e9)
    assert 29.0 < gain < 32.0


def test_link_budget_closure():
    res = calculate_link_budget(
        frequency_band="X-Band",
        tx_power_w=15.0,
        antenna_type="Parabolic Dish",
        dish_diameter_m=0.5,
        target_data_rate_kbps=256.0,
        dsn_station_type="34m BWG",
    )

    # Standard 15W X-band link to 34m DSN BWG dish closes with healthy margin
    assert res.is_link_closed is True
    assert res.link_margin_db > 3.0
    assert res.max_achievable_data_rate_kbps > 500.0
    assert 1.25 < res.light_time_seconds < 1.35
