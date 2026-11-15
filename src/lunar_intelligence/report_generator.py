"""Mission summary reporting, HTML dossier generation, CSV, and JSON export."""

from __future__ import annotations

import csv
import io
import json
from dataclasses import asdict
from typing import Any, Dict, List

from .candidate_sites import build_moon_trek_url, build_quickmap_url
from .coordinates import LunarSite
from .explanation_engine import generate_site_explanation
from .landing_evaluator import SimulationEpochSample, SiteWindowSummary
from .mcda_engine import ScoredSiteRecord


def export_samples_to_csv(samples: List[SimulationEpochSample]) -> str:
    """Generate CSV string of all simulation epoch samples."""
    output = io.StringIO()
    writer = csv.writer(output)

    headers = [
        "timestamp_utc",
        "sun_elevation_deg",
        "sun_azimuth_deg",
        "sun_disc_fraction",
        "sun_terrain_occluded",
        "effective_solar_flux_w_m2",
        "is_lit",
        "earth_elevation_deg",
        "earth_azimuth_deg",
        "earth_effective_elevation_deg",
        "earth_terrain_occluded",
        "dte_los_available",
        "has_dsn_coverage",
        "active_dsn_stations",
        "dte_comms_closed",
        "co_visibility_available",
        "is_landing_window",
    ]
    writer.writerow(headers)

    for s in samples:
        writer.writerow([
            s.timestamp_utc,
            s.sun_elevation_deg,
            s.sun_azimuth_deg,
            s.sun_disc_fraction,
            s.sun_terrain_occluded,
            s.effective_solar_flux_w_m2,
            s.is_lit,
            s.earth_elevation_deg,
            s.earth_azimuth_deg,
            s.earth_effective_elevation_deg,
            s.earth_terrain_occluded,
            s.dte_los_available,
            s.has_dsn_coverage,
            ";".join(s.active_dsn_stations),
            s.dte_comms_closed,
            s.co_visibility_available,
            s.is_landing_window,
        ])

    return output.getvalue()


def generate_html_dossier(
    site: LunarSite,
    summary: SiteWindowSummary,
    score_record: ScoredSiteRecord | None = None,
) -> str:
    """Generate a clean, print-ready HTML Mission Intelligence Briefing Dossier."""
    explanation = generate_site_explanation(site, summary, score_record)
    quickmap_url = build_quickmap_url(site.latitude_deg, site.longitude_deg)
    trek_url = build_moon_trek_url(site.latitude_deg, site.longitude_deg)

    strengths_html = "".join(f"<li>{s}</li>" for s in explanation["key_strengths"])
    risks_html = "".join(f"<li>{r}</li>" for r in explanation["key_risks"])
    ops_html = "".join(f"<li>{o}</li>" for o in explanation["operational_considerations"])
    assump_html = "".join(f"<li>{a}</li>" for a in explanation["assumptions"])

    windows_rows = ""
    for w in summary.touchdown_windows:
        stns = ", ".join(w.active_dsn_stations) if w.active_dsn_stations else "None"
        windows_rows += f"""
        <tr>
            <td>{w.start_time_utc}</td>
            <td>{w.end_time_utc}</td>
            <td><strong>{w.duration_hours:.1f} hrs</strong></td>
            <td>{w.avg_sun_elevation_deg:.1f}°</td>
            <td>{w.avg_earth_elevation_deg:.1f}°</td>
            <td>{w.peak_solar_flux_w_m2:.1f} W/m²</td>
            <td>{stns}</td>
        </tr>
        """

    if not summary.touchdown_windows:
        windows_rows = "<tr><td colspan='7' style='text-align:center;'>No nominal landing windows found during this window</td></tr>"

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Lunar Mission Briefing Dossier - {site.site_id}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background: #0f141c;
            color: #d1d5db;
            padding: 30px;
            margin: 0;
            line-height: 1.6;
        }}
        .dossier-card {{
            max-width: 950px;
            margin: 0 auto;
            background: #171f2c;
            border: 1px solid #2d3748;
            border-radius: 12px;
            padding: 35px;
            box-shadow: 0 10px 25px rgba(0,0,0,0.5);
        }}
        h1 {{ color: #60a5fa; margin-top: 0; border-bottom: 2px solid #2563eb; padding-bottom: 12px; font-size: 26px; }}
        h2 {{ color: #93c5fd; margin-top: 25px; font-size: 19px; border-bottom: 1px solid #374151; padding-bottom: 6px; }}
        .badge {{ display: inline-block; padding: 4px 10px; border-radius: 6px; font-size: 13px; font-weight: 600; }}
        .badge-prime {{ background: #065f46; color: #34d399; }}
        .badge-site {{ background: #1e3a8a; color: #bfdbfe; }}
        .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin: 20px 0; }}
        .stat-box {{ background: #0f172a; padding: 15px; border-radius: 8px; border: 1px solid #1e293b; }}
        .stat-box .label {{ font-size: 12px; color: #94a3b8; text-transform: uppercase; }}
        .stat-box .val {{ font-size: 22px; font-weight: 700; color: #f8fafc; margin-top: 5px; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 15px; font-size: 14px; }}
        th, td {{ padding: 10px 12px; border: 1px solid #334155; text-align: left; }}
        th {{ background: #1e293b; color: #cbd5e1; }}
        ul {{ padding-left: 20px; }}
        li {{ margin-bottom: 6px; }}
        .strengths li {{ color: #6ee7b7; }}
        .risks li {{ color: #fca5a5; }}
        .btn-link {{
            display: inline-block;
            background: #2563eb;
            color: #fff;
            text-decoration: none;
            padding: 8px 16px;
            border-radius: 6px;
            font-size: 14px;
            margin-right: 10px;
            margin-top: 15px;
        }}
        .btn-link:hover {{ background: #1d4ed8; }}
        .print-btn {{ background: #475569; }}
    </style>
</head>
<body>
    <div class="dossier-card">
        <div>
            <span class="badge badge-site">{site.region}</span>
            <span class="badge badge-prime">MCDA Rank #{score_record.rank if score_record else 1}</span>
        </div>
        <h1>Lunar Landing Site Intelligence Briefing</h1>
        <p><strong>Site:</strong> {site.name} ({site.site_id})<br>
        <strong>Coordinates:</strong> {site.latitude_deg:.4f}° Lat, {site.longitude_deg:.4f}° Lon | <strong>Elevation:</strong> {site.elevation_m} m LOLA datum<br>
        <strong>Mission Window:</strong> {summary.start_time_utc} to {summary.end_time_utc} ({summary.total_duration_hours:.1f} hours sampled)</p>

        <p>{site.description}</p>

        <div class="grid">
            <div class="stat-box">
                <div class="label">Sunlight Availability</div>
                <div class="val">{summary.sunlight_fraction*100:.1f}%</div>
                <small>{summary.sunlight_duration_hours:.1f} hrs total</small>
            </div>
            <div class="stat-box">
                <div class="label">Direct Earth LOS</div>
                <div class="val">{summary.earth_los_fraction*100:.1f}%</div>
                <small>{summary.earth_los_duration_hours:.1f} hrs clear</small>
            </div>
            <div class="stat-box">
                <div class="label">Co-Visibility Duration</div>
                <div class="val">{summary.co_visibility_fraction*100:.1f}%</div>
                <small>{summary.co_visibility_duration_hours:.1f} hrs active</small>
            </div>
            <div class="stat-box">
                <div class="label">Max Continuous Sunlight</div>
                <div class="val">{summary.longest_continuous_sunlight_hours:.1f} h</div>
                <small>Dark gap: {summary.longest_dark_period_hours:.1f} h</small>
            </div>
            <div class="stat-box">
                <div class="label">Mean Terrain Slope</div>
                <div class="val">{site.mean_slope_deg:.1f}°</div>
                <small>Roughness: {site.roughness_score:.2f}</small>
            </div>
            <div class="stat-box">
                <div class="label">Landing Windows</div>
                <div class="val">{len(summary.touchdown_windows)}</div>
                <small>{summary.total_landing_window_hours:.1f} hrs total</small>
            </div>
        </div>

        <h2>Scientific & Operational Evaluation</h2>
        <p>{explanation.get("rank_explanation", "")}</p>

        <h3>Key Mission Strengths</h3>
        <ul class="strengths">{strengths_html if strengths_html else "<li>None highlighted</li>"}</ul>

        <h3>Identified Hazards & Constraints</h3>
        <ul class="risks">{risks_html if risks_html else "<li>No critical hazards exceeding thresholds</li>"}</ul>

        <h2>Identified Landing & Touchdown Windows</h2>
        <p>Criteria: Sun elevation 5°–20° (surface relief contrast), Earth elevation &ge; 5°, active DSN station contact, unobstructed terrain.</p>
        <table>
            <thead>
                <tr>
                    <th>Start Window (UTC)</th>
                    <th>End Window (UTC)</th>
                    <th>Duration</th>
                    <th>Avg Sun El</th>
                    <th>Avg Earth El</th>
                    <th>Peak Solar Flux</th>
                    <th>DSN Stations</th>
                </tr>
            </thead>
            <tbody>
                {windows_rows}
            </tbody>
        </table>

        <h2>External Planetary Cartography Portals</h2>
        <a class="btn-link" href="{quickmap_url}" target="_blank">Open in LROC QuickMap</a>
        <a class="btn-link" href="{trek_url}" target="_blank">Open in NASA Moon Trek</a>
        <button class="btn-link print-btn" onclick="window.print()">Print Dossier</button>

        <h2>Model Assumptions & Reference System</h2>
        <ul style="font-size: 13px; color: #94a3b8;">
            {assump_html}
        </ul>
    </div>
</body>
</html>"""
    return html
