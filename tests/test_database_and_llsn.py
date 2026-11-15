"""Unit tests for SQLite database persistence and upgraded LLSN terrain endpoints."""

import pytest
from fastapi.testclient import TestClient
from lunar_intelligence.api import app
from lunar_intelligence.database import create_site, get_site, list_sites, save_assessment, list_assessments

client = TestClient(app)


def test_database_crud():
    # 1. Create a site
    site = create_site("Test Crater Alpha", -88.5, 45.0)
    assert site["name"] == "Test Crater Alpha"
    assert site["latitude"] == -88.5
    assert site["longitude"] == 45.0
    site_id = site["id"]

    # 2. Get site
    fetched = get_site(site_id)
    assert fetched is not None
    assert fetched["name"] == "Test Crater Alpha"

    # 3. Save assessment snapshot
    payload = {"status": "EVALUATED", "score": 88.5}
    snap = save_assessment(site_id, "2026-12-01T00:00:00Z", payload)
    assert snap["id"] > 0

    # 4. List assessments
    history = list_assessments(site_id)
    assert len(history) >= 1
    assert history[0]["assessment"]["status"] == "EVALUATED"

    # 5. List all sites
    all_sites = list_sites()
    assert len(all_sites) >= 1


def test_health_endpoint():
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert data["sqlite_database"] == "connected"


def test_terrain_status_endpoint():
    resp = client.get("/terrain/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "AVAILABLE"
    assert data["data_available"] is True


def test_upgraded_terrain_assessment_endpoint():
    # Test that /terrain/assessment now returns EVALUATED scientific data rather than NOT_EVALUATED
    resp = client.get("/terrain/assessment?latitude=-89.5&longitude=0.0&timestamp_utc=2026-12-01T00:00:00Z")
    assert resp.status_code == 200
    data = resp.json()
    assert "results" in data
    
    # Check that all results have status EVALUATED
    for r in data["results"]:
        assert r["status"] == "EVALUATED"
        assert r["value"] is not None

    keys = [r["key"] for r in data["results"]]
    assert "sun_visibility" in keys
    assert "earth_visibility" in keys
    assert "terrain" in keys
    assert "thermal" in keys
    assert "hazards" in keys
    assert "suitability" in keys


def test_saved_sites_endpoints():
    # POST /sites
    post_resp = client.post("/sites", json={"name": "Candidate Shackleton", "latitude": -89.6, "longitude": 129.8})
    assert post_resp.status_code == 200
    site_data = post_resp.json()
    site_id = site_data["id"]

    # GET /sites
    list_resp = client.get("/sites")
    assert list_resp.status_code == 200
    sites = list_resp.json()["sites"]
    assert any(s["id"] == site_id for s in sites)

    # POST /sites/{id}/assessments
    snap_resp = client.post(f"/sites/{site_id}/assessments", json={"timestamp_utc": "2026-12-01T12:00:00Z"})
    assert snap_resp.status_code == 200
    assert snap_resp.json()["assessment"]["results"][0]["status"] == "EVALUATED"

    # GET /sites/{id}/history
    hist_resp = client.get(f"/sites/{site_id}/history")
    assert hist_resp.status_code == 200
    assert len(hist_resp.json()["assessments"]) >= 1
