"""Landing site time-series simulation, co-visibility, and landing window detection."""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

from .config import ModelConfig
from .coordinates import LunarSite
from .dsn_coverage import calculate_dsn_coverage
from .earth_intelligence import calculate_earth_state
from .solar_intelligence import calculate_solar_state
from .terrain_horizon import evaluate_terrain_occlusion
from .time_system import format_utc, generate_time_steps


@dataclass(frozen=True)
class SimulationEpochSample:
    """Sample of site environment and visibility at a specific timestamp."""
    timestamp_utc: str
    
    # Solar
    sun_elevation_deg: float
    sun_azimuth_deg: float
    sun_disc_fraction: float
    sun_terrain_occluded: bool
    effective_solar_flux_w_m2: float
    is_lit: bool
    
    # Earth & Comms
    earth_elevation_deg: float
    earth_azimuth_deg: float
    earth_effective_elevation_deg: float
    earth_terrain_occluded: bool
    dte_los_available: bool
    active_dsn_stations: List[str]
    has_dsn_coverage: bool
    dte_comms_closed: bool  # DTE LOS available AND DSN station tracking
    
    # Combined Co-visibility & Landing criteria
    co_visibility_available: bool  # Both lit AND comms available
    is_landing_window: bool        # Sun 5°-20°, Earth >= 5°, DSN contact, not terrain occluded


@dataclass(frozen=True)
class TouchdownWindow:
    """A continuous window suitable for landing touchdown."""
    start_time_utc: str
    end_time_utc: str
    duration_hours: float
    avg_sun_elevation_deg: float
    avg_earth_elevation_deg: float
    peak_solar_flux_w_m2: float
    active_dsn_stations: List[str]


@dataclass(frozen=True)
class SiteWindowSummary:
    """Consolidated performance metrics of a lunar site across the simulation window."""
    site_id: str
    start_time_utc: str
    end_time_utc: str
    total_duration_hours: float
    sample_step_seconds: float
    total_samples: int
    
    # Illumination metrics
    sunlight_duration_hours: float
    sunlight_fraction: float
    longest_continuous_sunlight_hours: float
    longest_dark_period_hours: float
    max_solar_elevation_deg: float
    min_solar_elevation_deg: float
    peak_solar_flux_w_m2: float
    
    # Earth visibility & communications metrics
    earth_los_duration_hours: float
    earth_los_fraction: float
    longest_continuous_earth_los_hours: float
    longest_comms_blackout_hours: float
    max_earth_elevation_deg: float
    min_earth_elevation_deg: float
    dsn_closed_duration_hours: float
    dsn_closed_fraction: float
    
    # Combined co-visibility & landing metrics
    co_visibility_duration_hours: float
    co_visibility_fraction: float
    touchdown_windows: List[TouchdownWindow]
    total_landing_window_hours: float


def run_site_simulation(
    site: LunarSite,
    start_utc: str,
    end_utc: str,
    step_seconds: float = 3600.0,
    antenna_mast_height_m: float = 2.0,
    config: Optional[ModelConfig] = None,
) -> tuple[List[SimulationEpochSample], SiteWindowSummary]:
    """Execute complete temporal simulation for a candidate landing site."""
    cfg = config or ModelConfig()
    timestamps = generate_time_steps(start_utc, end_utc, step_seconds)

    samples: List[SimulationEpochSample] = []

    for dt in timestamps:
        ts_utc = format_utc(dt)

        # 1. Solar
        solar = calculate_solar_state(site, ts_utc, cfg)
        solar_occ = evaluate_terrain_occlusion(
            site, solar.elevation_deg, solar.azimuth_deg, solar.angular_radius_deg
        )
        is_lit = solar.upper_limb_above_horizon and not solar_occ.is_occluded_by_terrain
        effective_flux = solar.incident_flux_horizontal_w_m2 * solar_occ.partial_terrain_factor

        # 2. Earth
        earth = calculate_earth_state(
            site,
            ts_utc,
            antenna_mast_height_m=antenna_mast_height_m,
            min_elevation_deg=cfg.min_earth_elevation_deg,
            config=cfg,
        )
        earth_occ = evaluate_terrain_occlusion(
            site, earth.effective_elevation_deg, earth.azimuth_deg, earth.angular_radius_deg
        )
        dte_los = earth.dte_los_available and not earth_occ.is_occluded_by_terrain

        # 3. DSN Ground Station tracking
        dsn = calculate_dsn_coverage(ts_utc)
        dte_closed = dte_los and dsn.has_dsn_contact

        # 4. Co-visibility
        co_vis = is_lit and dte_closed

        # 5. Landing window
        # Sun elevation 5° to 20° provides good shadow contrast for pilot & optical hazard recognition
        sun_in_band = cfg.touchdown_sun_min_deg <= solar.elevation_deg <= cfg.touchdown_sun_max_deg
        earth_safe_el = earth.effective_elevation_deg >= 5.0
        is_landing = sun_in_band and earth_safe_el and dte_closed and not solar_occ.is_occluded_by_terrain

        samples.append(
            SimulationEpochSample(
                timestamp_utc=ts_utc,
                sun_elevation_deg=solar.elevation_deg,
                sun_azimuth_deg=solar.azimuth_deg,
                sun_disc_fraction=solar.disc_illuminated_fraction,
                sun_terrain_occluded=solar_occ.is_occluded_by_terrain,
                effective_solar_flux_w_m2=round(effective_flux, 2),
                is_lit=is_lit,
                earth_elevation_deg=earth.elevation_deg,
                earth_azimuth_deg=earth.azimuth_deg,
                earth_effective_elevation_deg=earth.effective_elevation_deg,
                earth_terrain_occluded=earth_occ.is_occluded_by_terrain,
                dte_los_available=dte_los,
                active_dsn_stations=dsn.active_stations,
                has_dsn_coverage=dsn.has_dsn_contact,
                dte_comms_closed=dte_closed,
                co_visibility_available=co_vis,
                is_landing_window=is_landing,
            )
        )

    # Summarize metrics
    summary = compute_window_summary(site, samples, start_utc, end_utc, step_seconds)
    return samples, summary


def compute_window_summary(
    site: LunarSite,
    samples: List[SimulationEpochSample],
    start_utc: str,
    end_utc: str,
    step_seconds: float,
) -> SiteWindowSummary:
    """Compute aggregated performance metrics, durations, and landing windows."""
    if not samples:
        raise ValueError("Cannot summarize empty sample set")

    total_duration_hrs = (len(samples) - 1) * (step_seconds / 3600.0)
    if total_duration_hrs <= 0:
        total_duration_hrs = step_seconds / 3600.0

    step_hrs = step_seconds / 3600.0

    # 1. Illumination statistics
    lit_samples = [s for s in samples if s.is_lit]
    lit_hrs = len(lit_samples) * step_hrs
    lit_fraction = min(1.0, lit_hrs / total_duration_hrs)

    longest_lit_hrs = 0.0
    longest_dark_hrs = 0.0
    curr_lit = 0.0
    curr_dark = 0.0

    for s in samples:
        if s.is_lit:
            curr_lit += step_hrs
            longest_dark_hrs = max(longest_dark_hrs, curr_dark)
            curr_dark = 0.0
        else:
            curr_dark += step_hrs
            longest_lit_hrs = max(longest_lit_hrs, curr_lit)
            curr_lit = 0.0
    longest_lit_hrs = max(longest_lit_hrs, curr_lit)
    longest_dark_hrs = max(longest_dark_hrs, curr_dark)

    sun_elevations = [s.sun_elevation_deg for s in samples]
    max_sun_el = max(sun_elevations)
    min_sun_el = min(sun_elevations)
    peak_flux = max(s.effective_solar_flux_w_m2 for s in samples)

    # 2. Earth LOS & DSN statistics
    dte_los_samples = [s for s in samples if s.dte_los_available]
    dte_los_hrs = len(dte_los_samples) * step_hrs
    dte_los_fraction = min(1.0, dte_los_hrs / total_duration_hrs)

    dsn_closed_samples = [s for s in samples if s.dte_comms_closed]
    dsn_closed_hrs = len(dsn_closed_samples) * step_hrs
    dsn_closed_fraction = min(1.0, dsn_closed_hrs / total_duration_hrs)

    longest_earth_los_hrs = 0.0
    longest_blackout_hrs = 0.0
    curr_los = 0.0
    curr_blackout = 0.0

    for s in samples:
        if s.dte_comms_closed:
            curr_los += step_hrs
            longest_blackout_hrs = max(longest_blackout_hrs, curr_blackout)
            curr_blackout = 0.0
        else:
            curr_blackout += step_hrs
            longest_earth_los_hrs = max(longest_earth_los_hrs, curr_los)
            curr_los = 0.0
    longest_earth_los_hrs = max(longest_earth_los_hrs, curr_los)
    longest_blackout_hrs = max(longest_blackout_hrs, curr_blackout)

    earth_elevations = [s.earth_effective_elevation_deg for s in samples]
    max_earth_el = max(earth_elevations)
    min_earth_el = min(earth_elevations)

    # 3. Co-visibility
    covis_samples = [s for s in samples if s.co_visibility_available]
    covis_hrs = len(covis_samples) * step_hrs
    covis_fraction = min(1.0, covis_hrs / total_duration_hrs)

    # 4. Landing windows
    touchdown_windows: List[TouchdownWindow] = []
    in_window = False
    win_start_idx = 0

    for i, s in enumerate(samples):
        if s.is_landing_window and not in_window:
            in_window = True
            win_start_idx = i
        elif not s.is_landing_window and in_window:
            in_window = False
            win_samples = samples[win_start_idx:i]
            dur_hrs = len(win_samples) * step_hrs
            all_stns = set()
            for ws in win_samples:
                all_stns.update(ws.active_dsn_stations)
            touchdown_windows.append(
                TouchdownWindow(
                    start_time_utc=win_samples[0].timestamp_utc,
                    end_time_utc=win_samples[-1].timestamp_utc,
                    duration_hours=round(dur_hrs, 2),
                    avg_sun_elevation_deg=round(sum(ws.sun_elevation_deg for ws in win_samples) / len(win_samples), 2),
                    avg_earth_elevation_deg=round(sum(ws.earth_effective_elevation_deg for ws in win_samples) / len(win_samples), 2),
                    peak_solar_flux_w_m2=round(max(ws.effective_solar_flux_w_m2 for ws in win_samples), 2),
                    active_dsn_stations=sorted(list(all_stns)),
                )
            )

    if in_window:
        win_samples = samples[win_start_idx:]
        dur_hrs = len(win_samples) * step_hrs
        all_stns = set()
        for ws in win_samples:
            all_stns.update(ws.active_dsn_stations)
        touchdown_windows.append(
            TouchdownWindow(
                start_time_utc=win_samples[0].timestamp_utc,
                end_time_utc=win_samples[-1].timestamp_utc,
                duration_hours=round(dur_hrs, 2),
                avg_sun_elevation_deg=round(sum(ws.sun_elevation_deg for ws in win_samples) / len(win_samples), 2),
                avg_earth_elevation_deg=round(sum(ws.earth_effective_elevation_deg for ws in win_samples) / len(win_samples), 2),
                peak_solar_flux_w_m2=round(max(ws.effective_solar_flux_w_m2 for ws in win_samples), 2),
                active_dsn_stations=sorted(list(all_stns)),
            )
        )

    total_window_hrs = sum(tw.duration_hours for tw in touchdown_windows)

    return SiteWindowSummary(
        site_id=site.site_id,
        start_time_utc=start_utc,
        end_time_utc=end_utc,
        total_duration_hours=round(total_duration_hrs, 2),
        sample_step_seconds=step_seconds,
        total_samples=len(samples),
        sunlight_duration_hours=round(lit_hrs, 2),
        sunlight_fraction=round(lit_fraction, 4),
        longest_continuous_sunlight_hours=round(longest_lit_hrs, 2),
        longest_dark_period_hours=round(longest_dark_hrs, 2),
        max_solar_elevation_deg=round(max_sun_el, 2),
        min_solar_elevation_deg=round(min_sun_el, 2),
        peak_solar_flux_w_m2=round(peak_flux, 2),
        earth_los_duration_hours=round(dte_los_hrs, 2),
        earth_los_fraction=round(dte_los_fraction, 4),
        longest_continuous_earth_los_hours=round(longest_earth_los_hrs, 2),
        longest_comms_blackout_hours=round(longest_blackout_hrs, 2),
        max_earth_elevation_deg=round(max_earth_el, 2),
        min_earth_elevation_deg=round(min_earth_el, 2),
        dsn_closed_duration_hours=round(dsn_closed_hrs, 2),
        dsn_closed_fraction=round(dsn_closed_fraction, 4),
        co_visibility_duration_hours=round(covis_hrs, 2),
        co_visibility_fraction=round(covis_fraction, 4),
        touchdown_windows=touchdown_windows,
        total_landing_window_hours=round(total_window_hrs, 2),
    )
