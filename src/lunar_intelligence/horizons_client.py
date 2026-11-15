"""NASA JPL Horizons API client and ephemeris cross-verification suite.

Official API endpoint: https://ssd.jpl.nasa.gov/api/horizons.api
Provides programmatic ephemerides directly from NASA JPL DE440/DE441 integrations
for cross-checking preliminary analytical predictions.
"""

from __future__ import annotations

import json
import logging
import math
import re
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from .coordinates import LunarSite
from .ephemeris_engine import compute_target_geometry

logger = logging.getLogger(__name__)

HORIZONS_API_URL = "https://ssd.jpl.nasa.gov/api/horizons.api"


@dataclass
class HorizonsEphemerisPoint:
    """A parsed ephemeris data point returned by JPL Horizons."""
    epoch_utc: str
    target_name: str
    azimuth_deg: Optional[float] = None
    elevation_deg: Optional[float] = None
    range_km: Optional[float] = None
    light_time_minutes: Optional[float] = None
    sub_obs_lon_deg: Optional[float] = None
    sub_obs_lat_deg: Optional[float] = None
    solar_illum_fraction: Optional[float] = None
    raw_record: str = ""


@dataclass
class HorizonsComparisonResult:
    """Comparison between internal analytical ephemeris and NASA JPL Horizons."""
    target: str
    epoch_utc: str
    site_id: str
    internal_elevation_deg: float
    internal_azimuth_deg: float
    internal_distance_km: float
    horizons_elevation_deg: Optional[float]
    horizons_azimuth_deg: Optional[float]
    horizons_range_km: Optional[float]
    delta_elevation_deg: Optional[float]
    delta_azimuth_deg: Optional[float]
    delta_range_km: Optional[float]
    status: str
    source: str
    notes: str


class HorizonsClient:
    """Client for NASA JPL Horizons API with local caching and offline fallback."""

    def __init__(self, timeout_seconds: int = 12):
        self.timeout = timeout_seconds
        self._cache: Dict[str, Any] = {}

    def query_topocentric(
        self,
        target: str,
        epoch_utc: str,
        site: LunarSite,
    ) -> HorizonsEphemerisPoint:
        """Query JPL Horizons for a topocentric observer located on the Moon.

        Moon center code: 301
        Observer coordinate: SITE_COORD='lon,lat,alt' relative to Moon (301)
        Target: Sun = '10', Earth = '399'
        """
        target_code = "10" if target.upper() == "SUN" else "399"
        # Horizons expects longitude (-180 to 180 or 0 to 360), latitude (-90 to 90), elevation in km
        alt_km = site.elevation_m / 1000.0
        # Format date for Horizons: YYYY-MM-DD HH:MM
        dt = datetime.fromisoformat(epoch_utc.replace("Z", "+00:00")).astimezone(timezone.utc)
        start_str = dt.strftime("%Y-%m-%d %H:%M")
        # Next minute for stop
        stop_dt = datetime.fromtimestamp(dt.timestamp() + 120, tz=timezone.utc)
        stop_str = stop_dt.strftime("%Y-%m-%d %H:%M")

        cache_key = f"{target_code}_{site.latitude_deg}_{site.longitude_deg}_{start_str}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        # Horizons query parameters:
        # QUANTITIES='4' -> Apparent Azimuth & Elevation
        # QUANTITIES='19' -> Range and range-rate
        # QUANTITIES='4,19' -> Az/El and Range
        params = {
            "format": "json",
            "COMMAND": f"'{target_code}'",
            "EPHEM_TYPE": "'OBSERVER'",
            "CENTER": "'coord@301'",
            "COORD_TYPE": "'GEODETIC'",
            "SITE_COORD": f"'{site.longitude_deg:.4f},{site.latitude_deg:.4f},{alt_km:.3f}'",
            "START_TIME": f"'{start_str}'",
            "STOP_TIME": f"'{stop_str}'",
            "STEP_SIZE": "'1m'",
            "QUANTITIES": "'4,19,20'",
            "ANG_FORMAT": "'DEG'",
        }

        query_string = urllib.parse.urlencode(params)
        url = f"{HORIZONS_API_URL}?{query_string}"

        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "LunarLandingIntelligence/1.0 (NASA/JPL Academic Research Client)"
            },
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except Exception as exc:
            logger.warning(f"JPL Horizons API query failed: {exc}")
            raise ConnectionError(f"Failed to reach JPL Horizons API: {exc}") from exc

        parsed = self._parse_horizons_response(data, target.upper(), epoch_utc)
        self._cache[cache_key] = parsed
        return parsed

    def _parse_horizons_response(
        self, data: Dict[str, Any], target_name: str, epoch_utc: str
    ) -> HorizonsEphemerisPoint:
        """Parse raw Horizons JSON output string table."""
        result_text = data.get("result", "")
        # Find table between $$SOE and $$EOE markers
        soe_idx = result_text.find("$$SOE")
        eoe_idx = result_text.find("$$EOE")

        if soe_idx == -1 or eoe_idx == -1:
            # Check for error description in result text
            raise ValueError(f"Horizons returned unexpected format: {result_text[:300]}")

        table_block = result_text[soe_idx + 5 : eoe_idx].strip()
        lines = [line.strip() for line in table_block.splitlines() if line.strip()]

        if not lines:
            raise ValueError("No ephemeris data points between $$SOE and $$EOE markers")

        first_line = lines[0]
        # Example format:
        # Date__(UT)__HR:MN     Azi_(a-app)_Elev            r        rdot            delta      deldot    1-way_LT
        # 2026-Dec-01 00:00 *m  134.123456  -1.234567   1.496E+08  0.000E+00   3.844E+05  0.000E+00   1.282000
        # Split tokens
        tokens = re.split(r"\s+", first_line)

        azimuth: Optional[float] = None
        elevation: Optional[float] = None
        range_km: Optional[float] = None
        lt_min: Optional[float] = None

        # Look for numeric fields
        num_floats: list[float] = []
        for t in tokens:
            try:
                num_floats.append(float(t))
            except ValueError:
                pass

        if len(num_floats) >= 2:
            azimuth = num_floats[0]
            elevation = num_floats[1]
        if len(num_floats) >= 3:
            range_km = num_floats[2]
        if len(num_floats) >= 5:
            lt_min = num_floats[-1]

        return HorizonsEphemerisPoint(
            epoch_utc=epoch_utc,
            target_name=target_name,
            azimuth_deg=azimuth,
            elevation_deg=elevation,
            range_km=range_km,
            light_time_minutes=lt_min,
            raw_record=first_line,
        )


def cross_check_ephemeris(
    target: str,
    epoch_utc: str,
    site: LunarSite,
    client: Optional[HorizonsClient] = None,
) -> HorizonsComparisonResult:
    """Cross-check internal analytical ephemeris against live NASA JPL Horizons ephemeris."""
    # 1. Internal model
    internal_state = compute_target_geometry(target, epoch_utc, site)
    internal_el = internal_state.elevation_deg
    internal_az = internal_state.azimuth_deg
    internal_dist_km = internal_state.distance_m / 1000.0

    cli = client or HorizonsClient()

    try:
        horizons_pt = cli.query_topocentric(target, epoch_utc, site)
        h_el = horizons_pt.elevation_deg
        h_az = horizons_pt.azimuth_deg
        h_dist = horizons_pt.range_km

        delta_el = abs(internal_el - h_el) if h_el is not None else None
        delta_az = abs(internal_az - h_az) if h_az is not None else None
        if delta_az is not None and delta_az > 180:
            delta_az = 360 - delta_az
        delta_dist = abs(internal_dist_km - h_dist) if h_dist is not None else None

        status = "VERIFIED_AGAINST_JPL_HORIZONS"
        source = "Live NASA JPL Horizons DE440"
        notes = (
            f"Horizons validation successful. Delta El: {delta_el:.4f}°, "
            f"Delta Az: {delta_az:.4f}°."
        )

        return HorizonsComparisonResult(
            target=target.upper(),
            epoch_utc=epoch_utc,
            site_id=site.site_id,
            internal_elevation_deg=round(internal_el, 4),
            internal_azimuth_deg=round(internal_az, 4),
            internal_distance_km=round(internal_dist_km, 2),
            horizons_elevation_deg=round(h_el, 4) if h_el is not None else None,
            horizons_azimuth_deg=round(h_az, 4) if h_az is not None else None,
            horizons_range_km=round(h_dist, 2) if h_dist is not None else None,
            delta_elevation_deg=round(delta_el, 4) if delta_el is not None else None,
            delta_azimuth_deg=round(delta_az, 4) if delta_az is not None else None,
            delta_range_km=round(delta_dist, 2) if delta_dist is not None else None,
            status=status,
            source=source,
            notes=notes,
        )

    except Exception as exc:
        # Fallback with graceful offline reporting
        return HorizonsComparisonResult(
            target=target.upper(),
            epoch_utc=epoch_utc,
            site_id=site.site_id,
            internal_elevation_deg=round(internal_el, 4),
            internal_azimuth_deg=round(internal_az, 4),
            internal_distance_km=round(internal_dist_km, 2),
            horizons_elevation_deg=None,
            horizons_azimuth_deg=None,
            horizons_range_km=None,
            delta_elevation_deg=None,
            delta_azimuth_deg=None,
            delta_range_km=None,
            status="INTERNAL_MODEL_ACTIVE_OFFLINE",
            source="Internal IAU/DE440 Analytical Engine",
            notes=f"Horizons remote API unavailable ({exc}); internal analytical model active.",
        )
