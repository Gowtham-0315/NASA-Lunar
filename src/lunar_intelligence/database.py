"""SQLite database persistence for saved lunar sites and assessment snapshots.

Interfacing with data/llsn.sqlite3, maintaining full compatibility with the
Lunar Landing Site Navigator (LLSN) schema and history tracking.
"""

from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

DATABASE_PATH = Path(__file__).resolve().parents[2] / "data" / "llsn.sqlite3"


def _connect() -> sqlite3.Connection:
    """Establish connection to SQLite database with foreign keys and dict-like row factory."""
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DATABASE_PATH, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_database() -> None:
    """Initialize SQLite database tables and indexes."""
    with _connect() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS sites (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                latitude REAL NOT NULL CHECK(latitude >= -90 AND latitude <= 90),
                longitude REAL NOT NULL CHECK(longitude >= -180 AND longitude <= 180),
                coordinate_convention TEXT NOT NULL DEFAULT 'UNSPECIFIED',
                created_at_utc TEXT NOT NULL,
                UNIQUE(name, latitude, longitude)
            );
            CREATE TABLE IF NOT EXISTS assessment_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                site_id INTEGER NOT NULL REFERENCES sites(id),
                timestamp_utc TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                created_at_utc TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_snapshots_site_time
                ON assessment_snapshots(site_id, created_at_utc DESC);
            """
        )


def create_site(name: str, latitude: float, longitude: float) -> Dict[str, Any]:
    """Create or return existing saved site in SQLite."""
    clean_name = name.strip()
    with _connect() as connection:
        connection.execute(
            "INSERT OR IGNORE INTO sites(name, latitude, longitude, created_at_utc) VALUES (?, ?, ?, ?)",
            (clean_name, latitude, longitude, datetime.now(timezone.utc).isoformat()),
        )
        row = connection.execute(
            "SELECT * FROM sites WHERE name = ? AND latitude = ? AND longitude = ?",
            (clean_name, latitude, longitude),
        ).fetchone()
        return dict(row) if row else {}


def get_site(site_id: int) -> Optional[Dict[str, Any]]:
    """Retrieve saved site by numeric ID."""
    with _connect() as connection:
        row = connection.execute("SELECT * FROM sites WHERE id = ?", (site_id,)).fetchone()
        return dict(row) if row else None


def list_sites() -> List[Dict[str, Any]]:
    """List all saved sites with assessment counts and last check timestamps."""
    with _connect() as connection:
        rows = connection.execute(
            """
            SELECT s.*, COUNT(a.id) AS assessment_count,
                   MAX(a.created_at_utc) AS last_assessed_at_utc
            FROM sites s LEFT JOIN assessment_snapshots a ON a.site_id = s.id
            GROUP BY s.id ORDER BY s.created_at_utc DESC
            """
        ).fetchall()
        return [dict(row) for row in rows]


def save_assessment(site_id: int, timestamp_utc: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Save an assessment snapshot payload for a site."""
    created_at = datetime.now(timezone.utc).isoformat()
    with _connect() as connection:
        cursor = connection.execute(
            "INSERT INTO assessment_snapshots(site_id, timestamp_utc, payload_json, created_at_utc) VALUES (?, ?, ?, ?)",
            (site_id, timestamp_utc, json.dumps(payload, allow_nan=False), created_at),
        )
        return {"id": cursor.lastrowid, "created_at_utc": created_at}


def list_assessments(site_id: int) -> List[Dict[str, Any]]:
    """Retrieve all assessment history snapshots for a saved site."""
    with _connect() as connection:
        rows = connection.execute(
            "SELECT * FROM assessment_snapshots WHERE site_id = ? ORDER BY created_at_utc DESC",
            (site_id,),
        ).fetchall()
        return [
            {
                "id": row["id"],
                "timestamp_utc": row["timestamp_utc"],
                "created_at_utc": row["created_at_utc"],
                "assessment": json.loads(row["payload_json"]),
            }
            for row in rows
        ]
