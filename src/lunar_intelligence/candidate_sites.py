"""Curated database of lunar landing sites, candidate regions, and external map links."""

from __future__ import annotations

from typing import Dict, List
from .coordinates import LunarSite


def build_quickmap_url(lat: float, lon: float, zoom: int = 12) -> str:
    """Generate direct deep-link to ASU LROC QuickMap centered on coordinates."""
    # LROC QuickMap uses zoom, center lat/lon, and default layers
    return f"https://quickmap.lroc.asu.edu/?extent={lon-0.5},{lat-0.5},{lon+0.5},{lat+0.5}&proj=10&layers=nrvr.lroc_wac_mosaic"


def build_moon_trek_url(lat: float, lon: float) -> str:
    """Generate direct deep-link to NASA Moon Trek interactive viewer."""
    return f"https://trek.nasa.gov/moon/#v=0.1&x={lon}&y={lat}&z=6&p=urn%3Aogc%3Adef%3Acrs%3AEPSG%3A%3A104903&d="


# Curated catalog of candidate lunar sites
CANDIDATE_SITES: Dict[str, LunarSite] = {
    # Canadian Space Agency Targets
    "CSA_ROVER_NOBILE": LunarSite(
        site_id="CSA_ROVER_NOBILE",
        name="Canadian Lunar Rover Primary Target (Nobile Rim)",
        latitude_deg=-85.25,
        longitude_deg=53.50,
        elevation_m=1200.0,
        region="South Pole / Nobile",
        description="Primary landing target for the Canadian Lunar Rover. High epithermal neutron hydrogen deficit indicating near-surface water ice reserves.",
        mean_slope_deg=5.8,
        roughness_score=0.32,
        scientific_priority=0.98,
    ),
    "CSA_ROVER_MALAPERT": LunarSite(
        site_id="CSA_ROVER_MALAPERT",
        name="Canadian Lunar Rover Secondary Target (Malapert Plateau)",
        latitude_deg=-85.90,
        longitude_deg=2.50,
        elevation_m=4800.0,
        region="South Pole / Malapert",
        description="High-altitude polar plateau offering extensive solar visibility (>80%) and exceptional direct line-of-sight to Earth for Canadian teleoperation.",
        mean_slope_deg=4.5,
        roughness_score=0.25,
        scientific_priority=0.92,
    ),
    "CSA_CONNECTING_RIDGE": LunarSite(
        site_id="CSA_CONNECTING_RIDGE",
        name="CSA Volatile Cold-Trap Scout (Connecting Ridge)",
        latitude_deg=-89.44,
        longitude_deg=222.60,
        elevation_m=2050.0,
        region="South Pole / Connecting Ridge",
        description="Narrow illuminated spine adjacent to Shackleton and de Gerlache permanently shadowed craters for short rover excursion sorties.",
        mean_slope_deg=5.4,
        roughness_score=0.31,
        scientific_priority=0.96,
    ),

    # NASA Artemis III Candidate Regions
    "SHACKLETON_RIM": LunarSite(
        site_id="SHACKLETON_RIM",
        name="Peak Near Shackleton (Artemis III Candidate)",
        latitude_deg=-89.60,
        longitude_deg=129.80,
        elevation_m=2150.0,
        region="South Pole Ultra-High Latitude",
        description="Prominent elevated rim point near Shackleton Crater. Features near-continuous summer illumination and constant line-of-sight to Earth.",
        mean_slope_deg=7.2,
        roughness_score=0.42,
        scientific_priority=0.99,
    ),
    "MALAPERT_MOUNTAIN": LunarSite(
        site_id="MALAPERT_MOUNTAIN",
        name="Malapert Mountain (Artemis III Candidate)",
        latitude_deg=-85.90,
        longitude_deg=0.00,
        elevation_m=5000.0,
        region="South Pole Highland Massif",
        description="5 km-high massif on the lunar near-side South Pole. One of the prime candidates for human surface habitats due to benign thermal conditions.",
        mean_slope_deg=4.8,
        roughness_score=0.28,
        scientific_priority=0.94,
    ),
    "CONNECTING_RIDGE": LunarSite(
        site_id="CONNECTING_RIDGE",
        name="Connecting Ridge (Artemis III Candidate)",
        latitude_deg=-89.40,
        longitude_deg=222.60,
        elevation_m=1950.0,
        region="South Pole Ridge",
        description="Topographic bridge between Shackleton and de Gerlache craters. Excellent access to multi-crater PSR ice deposits.",
        mean_slope_deg=5.4,
        roughness_score=0.31,
        scientific_priority=0.95,
    ),
    "DE_GERLACHE_RIM_1": LunarSite(
        site_id="DE_GERLACHE_RIM_1",
        name="de Gerlache Rim 1 (Artemis III Candidate)",
        latitude_deg=-88.50,
        longitude_deg=271.00,
        elevation_m=1400.0,
        region="South Pole / de Gerlache",
        description="Northern rim of de Gerlache crater. Moderately low slopes with good direct Earth visibility windows.",
        mean_slope_deg=6.0,
        roughness_score=0.33,
        scientific_priority=0.91,
    ),
    "HAWORTH_CRATER_RIM": LunarSite(
        site_id="HAWORTH_CRATER_RIM",
        name="Haworth Rim (Artemis III Candidate)",
        latitude_deg=-87.40,
        longitude_deg=355.00,
        elevation_m=1800.0,
        region="South Pole / Haworth",
        description="Deep crater with extensive water ice signatures detected by radar and spectroscopy; rim landing site.",
        mean_slope_deg=8.5,
        roughness_score=0.46,
        scientific_priority=0.93,
    ),
    "NOBILE_RIM_1": LunarSite(
        site_id="NOBILE_RIM_1",
        name="Nobile Rim 1 (Artemis III / VIPER Candidate)",
        latitude_deg=-85.20,
        longitude_deg=53.50,
        elevation_m=1100.0,
        region="South Pole / Nobile",
        description="Wide, relatively flat landing plain near scientific cold-traps selected for rover traverse corridors.",
        mean_slope_deg=6.1,
        roughness_score=0.35,
        scientific_priority=0.96,
    ),
    "FAUSTINI_RIM_A": LunarSite(
        site_id="FAUSTINI_RIM_A",
        name="Faustini Rim A (Artemis III Candidate)",
        latitude_deg=-87.20,
        longitude_deg=67.00,
        elevation_m=1750.0,
        region="South Pole / Faustini",
        description="Rugged rim terrain overlooking deep Faustini cold traps with substantial volatile sequestration potential.",
        mean_slope_deg=7.5,
        roughness_score=0.40,
        scientific_priority=0.92,
    ),
    "AMUNDSEN_RIM": LunarSite(
        site_id="AMUNDSEN_RIM",
        name="Amundsen Rim (Artemis III Candidate)",
        latitude_deg=-84.40,
        longitude_deg=85.00,
        elevation_m=850.0,
        region="South Pole Highland",
        description="Large crater rim providing transitional geologic access to South Pole-Aitken basin ejecta.",
        mean_slope_deg=6.8,
        roughness_score=0.36,
        scientific_priority=0.88,
    ),

    # Historic & Contemporary Robotic Landers
    "CHANDRAYAAN3_SHIV_SHAKTI": LunarSite(
        site_id="CHANDRAYAAN3_SHIV_SHAKTI",
        name="Chandrayaan-3 Shiv Shakti Point (ISRO 2023)",
        latitude_deg=-69.368,
        longitude_deg=32.348,
        elevation_m=-150.0,
        region="Southern Highland Plain",
        description="Historic landing location of ISRO's Vikram lander and Pragyan rover. First landing within 70 degrees of lunar South Pole.",
        mean_slope_deg=4.2,
        roughness_score=0.22,
        scientific_priority=0.85,
    ),
    "APOLLO11_MARE_TRANQUILLITATIS": LunarSite(
        site_id="APOLLO11_MARE_TRANQUILLITATIS",
        name="Apollo 11 Tranquility Base (NASA 1969)",
        latitude_deg=0.674,
        longitude_deg=23.473,
        elevation_m=-1250.0,
        region="Mare Tranquillitatis",
        description="First human landing site on the Moon. Equatorial basaltic plain with Earth directly overhead (zenith) at ~60° elevation.",
        mean_slope_deg=1.5,
        roughness_score=0.10,
        scientific_priority=0.80,
    ),
    "APOLLO17_TAURUS_LITTROW": LunarSite(
        site_id="APOLLO17_TAURUS_LITTROW",
        name="Apollo 17 Taurus-Littrow Valley (NASA 1972)",
        latitude_deg=20.191,
        longitude_deg=30.772,
        elevation_m=-2500.0,
        region="Taurus-Littrow Valley",
        description="Complex valley site flanked by North and South Massifs with pyroclastic orange soil deposits.",
        mean_slope_deg=5.1,
        roughness_score=0.28,
        scientific_priority=0.84,
    ),
    "CHANGE4_VON_KARMAN": LunarSite(
        site_id="CHANGE4_VON_KARMAN",
        name="Chang'e-4 Von Kármán Crater (CNSA 2019)",
        latitude_deg=-45.45,
        longitude_deg=177.59,
        elevation_m=-4200.0,
        region="Lunar Far Side / SPA Basin",
        description="First robotic landing on lunar far side. Earth is permanently occluded; requires Queqiao halo relay satellite.",
        mean_slope_deg=3.8,
        roughness_score=0.21,
        scientific_priority=0.90,
    ),
    "CHANGE6_SPA_BASIN": LunarSite(
        site_id="CHANGE6_SPA_BASIN",
        name="Chang'e-6 Apollo Basin Rim (CNSA 2024)",
        latitude_deg=-41.64,
        longitude_deg=206.01,
        elevation_m=-3900.0,
        region="Lunar Far Side / Apollo Basin",
        description="Historic first sample return from the lunar far side. Requires relay satellite communication.",
        mean_slope_deg=4.0,
        roughness_score=0.23,
        scientific_priority=0.95,
    ),
    "SLIM_SHIOLI_CRATER": LunarSite(
        site_id="SLIM_SHIOLI_CRATER",
        name="SLIM 'Moon Sniper' (JAXA 2024)",
        latitude_deg=-13.316,
        longitude_deg=25.251,
        elevation_m=-1800.0,
        region="Mare Nectaris Ejecta",
        description="Demonstrated pinpoint landing within 55 meters of target on a 15-degree crater slope.",
        mean_slope_deg=14.8,
        roughness_score=0.52,
        scientific_priority=0.82,
    ),
}


def get_all_sites() -> List[LunarSite]:
    """Retrieve all curated candidate and historic lunar sites."""
    return list(CANDIDATE_SITES.values())


def get_site_by_id(site_id: str) -> LunarSite | None:
    """Retrieve site by ID."""
    return CANDIDATE_SITES.get(site_id)
