# Lunar Landing Site Intelligence Platform

A mission-grade planetary intelligence application and analysis engine for lunar landing site selection, solar illumination, Earth visibility, Deep Space Network (DSN) communications, terrain-shadow occlusion, and Multi-Criteria Decision Analysis (MCDA) ranking.

Fully integrated with:
1. **LROC QuickMap (`quickmap.lroc.asu.edu`)**: High-resolution LOLA topography, slope distributions, NAC/WAC imagery, and coordinate deep-links.
2. **NASA Moon Trek (`trek.nasa.gov/moon`)**: Interactive 2D/3D lunar GIS basemap with WAC Global Mosaic WMTS tile services and altimetry.
3. **NASA JPL Horizons System (`ssd.jpl.nasa.gov/horizons`)**: Official live ephemeris API integration for cross-checking Sun/Earth topocentric vectors, sub-points, and libration against DE440 integrations.
4. **Canadian Space Agency Moon Exploration (`asc-csa.gc.ca/eng/astronomy/moon-exploration/`)**: Mission planning constraints for the Canadian Lunar Rover (Canadensys / NASA CLPS), Canadarm3 on the Lunar Gateway space station, and volatile prospecting in Permanently Shadowed Regions (PSRs).

---

## Architecture & Modules

```
lunar-landing-intelligence/
├── src/
│   └── lunar_intelligence/
│       ├── config.py             # Physical constants, DSN stations, RF bands, CSA constraints
│       ├── coordinates.py        # LunarSite, orthonormal ENU local frames, geodetic transformations
│       ├── time_system.py        # ISO 8601 UTC, Julian Date (JD), Ephemeris Time (ET), step generator
│       ├── ephemeris_engine.py   # High-precision IAU 2015 / Meeus / DE440 lunar orientation & vectors
│       ├── horizons_client.py    # Live NASA JPL Horizons API client and delta cross-checker
│       ├── solar_intelligence.py # Sun elevation/azimuth, disc fraction, penumbra, incident solar flux
│       ├── earth_intelligence.py # Earth elevation/azimuth, DTE LOS, antenna mast advantage, libration
│       ├── dsn_coverage.py       # Goldstone, Madrid, and Canberra tracking & handover scheduler
│       ├── link_budget.py        # S/X/Ka-band RF downlink budget, FSPL, EIRP, SNR margin, data rates
│       ├── terrain_horizon.py    # 360° LOLA DEM horizon profiles, crater rim shadow occlusion
│       ├── csa_exploration.py    # Canadian rover constraints (slope < 15°, PSR access, Canadarm3 relay)
│       ├── candidate_sites.py    # Curated catalog: Artemis III, Apollo, Chandrayaan-3, Chang'e, CSA
│       ├── mcda_engine.py        # WSM, TOPSIS, AHP, Pareto-optimal frontier, sensitivity analysis
│       ├── landing_evaluator.py  # Time-series simulation, co-visibility, touchdown window detection
│       ├── explanation_engine.py # Explainable natural-language scientific rationale
│       ├── report_generator.py   # Printable HTML mission briefing dossiers, CSV & JSON exports
│       └── api.py                # FastAPI REST API & static Single Page Application server
├── static/
│   ├── index.html                # Modern, dark-mode mission control single-page application
│   ├── app.js                    # Interactive controller: Leaflet Moon Trek map, Chart.js, sliders
│   └── styles.css                # Space-grade responsive dark theme styling
├── tests/                        # Full test suite covering ephemeris, solar, earth, DSN, MCDA, API
├── pyproject.toml
├── requirements.txt
└── run_app.py                    # One-command server launcher
```

---

## Quick Start

### 1. Run Unit Tests
```powershell
python -m pytest C:\Users\tharif\.gemini\antigravity\scratch\lunar-landing-intelligence\tests
```

### 2. Launch the Web Application
```powershell
cd C:\Users\tharif\.gemini\antigravity\scratch\lunar-landing-intelligence
python run_app.py
```
Open your browser to:
**`http://127.0.0.1:8000`**

---

## Features & Capabilities

- **Interactive Lunar Map**:
  - Pan and zoom across the Moon with NASA Moon Trek's high-resolution LRO WAC Global Mosaic.
  - Interactive pins for all 13 Artemis III candidate regions, Apollo 11–17 sites, Chandrayaan-3, Chang'e-4/6, SLIM, and Canadian Rover targets.
  - Click anywhere on the lunar surface to inspect coordinates and evaluate custom landing sites.
  - Direct 1-click launch to LROC QuickMap and NASA Moon Trek.
- **Solar & Earth Dynamics**:
  - Solar elevation, azimuth, and disc fraction calculated using finite-disk circular segment geometry.
  - Earth elevation, azimuth, and direct line-of-sight tracking with antenna mast height adjustments.
  - Incident solar irradiance (W/m²) modeled for both horizontal surface and tilted solar arrays.
- **360° Polar Sky & Horizon Profiles**:
  - Radar plot of crater rim topographic obstruction angles from 0° to 360° azimuth.
  - Sun and Earth trajectory tracks plotted against terrain boundaries.
- **Deep Space Network (DSN) & RF Link Budget**:
  - Real-time 24/7 tracking across Goldstone (USA), Madrid (Spain), and Canberra (Australia).
  - Interactive downlink budget calculator for S-band (2.25 GHz), X-band (8.45 GHz), and Ka-band (32 GHz).
  - Sliders for RF power, lander antenna dish diameter, and target data rates.
- **Multi-Criteria Decision Analysis (MCDA)**:
  - Weighted Sum Model (WSM) and TOPSIS (Technique for Order Preference by Similarity to Ideal Solution).
  - Identification of the Pareto-optimal trade-off frontier.
  - Dynamic weight sliders with real-time recalculation of site rankings and radar comparison charts.
- **Canadian Space Agency (CSA) Exploration**:
  - Evaluation of landing sites against Canadian micro-rover constraints (slope < 15°, minimum 48h continuous sunlight, solar flux > 200 W/m²).
  - Canadian Lunar Rover instrument suite overview (LHCI hydrogen imager, DTVA volatile analyzer, 360 NavCam, radiation sensor).
  - Canadarm3 on Lunar Gateway orbital coverage and polar communication relay assessment.
- **Live JPL Horizons API Ephemeris Cross-Verification**:
  - Query NASA JPL Horizons REST API directly to cross-check topocentric Sun and Earth vectors against official DE440 ephemerides.
- **Mission Export & Reporting**:
  - One-click print-ready HTML Mission Briefing Dossier.
  - Complete time-series CSV export for CAD and trajectory tools.
