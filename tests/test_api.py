"""Unit tests for FastAPI endpoints."""

from fastapi.testclient import TestClient
from lunar_intelligence.api import app

client = TestClient(app)


def test_get_sites():
    resp = client.get("/api/sites")
    assert resp.status_code == 200
    data = resp.json()
    assert "sites" in data
    assert len(data["sites"]) >= 10
    # Verify QuickMap and Moon Trek links exist
    first_site = data["sites"][0]
    assert "quickmap_url" in first_site
    assert "moon_trek_url" in first_site


def test_evaluate_endpoint():
    req_body = {
        "site_id": "SHACKLETON_RIM",
        "start_utc": "2026-12-01T00:00:00Z",
        "end_utc": "2026-12-02T00:00:00Z",
        "step_seconds": 3600.0,
        "antenna_mast_height_m": 2.0,
    }
    resp = client.post("/api/evaluate", json=req_body)
    assert resp.status_code == 200
    data = resp.json()
    assert "summary" in data
    assert "horizon_mask" in data
    assert "csa_compliance" in data
    assert "samples" in data
    assert data["summary"]["total_samples"] == 25


def test_link_budget_endpoint():
    req_body = {
        "frequency_band": "X-Band",
        "tx_power_w": 15.0,
        "antenna_type": "Parabolic Dish",
        "dish_diameter_m": 0.5,
        "target_data_rate_kbps": 256.0,
        "dsn_station_type": "34m BWG",
    }
    resp = client.post("/api/link-budget", json=req_body)
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_link_closed"] is True
    assert data["link_margin_db"] > 0


def test_csa_overview_endpoint():
    resp = client.get("/api/csa-overview")
    assert resp.status_code == 200
    data = resp.json()
    assert "canadarm3" in data
    assert "rover_payloads" in data
    assert len(data["rover_payloads"]) >= 4
