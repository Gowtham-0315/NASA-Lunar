"""Time system conversions: UTC, Julian Date (JD), Ephemeris Time (ET/TDB), and time step generator."""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
import math
from typing import Generator, Sequence


def parse_utc(iso_string: str) -> datetime:
    """Parse an ISO 8601 UTC timestamp string into a timezone-aware UTC datetime."""
    clean = iso_string.strip()
    if clean.endswith("Z"):
        clean = clean[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(clean)
    except ValueError as exc:
        raise ValueError(f"Invalid ISO 8601 timestamp: '{iso_string}'") from exc
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def format_utc(dt: datetime) -> str:
    """Format a datetime into standard ISO 8601 UTC string (YYYY-MM-DDTHH:MM:SSZ)."""
    utc_dt = dt.astimezone(timezone.utc)
    return utc_dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def datetime_to_jd(dt: datetime) -> float:
    """Convert UTC datetime to Julian Date (JD)."""
    utc = dt.astimezone(timezone.utc)
    year = utc.year
    month = utc.month
    day = utc.day
    hour = utc.hour
    minute = utc.minute
    second = utc.second + utc.microsecond / 1e6

    if month <= 2:
        year -= 1
        month += 12

    a = math.floor(year / 100)
    b = 2 - a + math.floor(a / 4)

    day_fraction = (hour + (minute + second / 60.0) / 60.0) / 24.0
    jd = math.floor(365.25 * (year + 4716)) + math.floor(30.6001 * (month + 1)) + day + b - 1524.5 + day_fraction
    return jd


def jd_to_centuries_j2000(jd: float) -> float:
    """Calculate Julian centuries since standard epoch J2000.0 (JD 2451545.0)."""
    return (jd - 2451545.0) / 36525.0


def utc_to_et(iso_string: str) -> float:
    """Convert UTC ISO string to approximate Ephemeris Time (ET seconds past J2000.0).

    Takes into account accumulated leap seconds (currently 37s) + TT offset (32.184s) = ~69.184s.
    """
    dt = parse_utc(iso_string)
    jd = datetime_to_jd(dt)
    # Seconds past J2000.0
    utc_seconds = (jd - 2451545.0) * 86400.0
    delta_t = 69.184  # TT - UTC approximation
    return utc_seconds + delta_t


def generate_time_steps(start_utc: str, end_utc: str, step_seconds: float) -> list[datetime]:
    """Generate sequence of datetime timestamps between start and end (inclusive)."""
    start = parse_utc(start_utc)
    end = parse_utc(end_utc)

    if end < start:
        raise ValueError("end_utc must be greater than or equal to start_utc")
    if step_seconds <= 0:
        raise ValueError("step_seconds must be strictly positive")

    step = timedelta(seconds=step_seconds)
    steps: list[datetime] = []
    current = start

    # Maximum 50,000 steps limit to prevent excessive memory usage
    max_steps = 50000
    count = 0

    while current < end and count < max_steps:
        steps.append(current)
        current += step
        count += 1

    if not steps or steps[-1] != end:
        steps.append(end)

    return steps
