"""Direct-to-Earth (DTE) RF communications link budget calculator."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, Optional

from .config import BOLTZMANN_CONSTANT, RF_BANDS, SPEED_OF_LIGHT_M_S


@dataclass(frozen=True)
class LinkBudgetResult:
    """Detailed RF communication link budget analysis result."""
    frequency_band: str
    frequency_hz: float
    wavelength_m: float
    distance_km: float
    light_time_seconds: float
    
    # Transmitter parameters
    tx_power_w: float
    tx_power_dbw: float
    antenna_type: str
    dish_diameter_m: Optional[float]
    tx_antenna_gain_dbi: float
    tx_line_loss_db: float
    tx_pointing_loss_db: float
    eirp_dbw: float
    
    # Path & propagation
    fspl_db: float
    atm_loss_db: float
    total_path_loss_db: float
    
    # Receiver (DSN)
    dsn_station_type: str
    rx_gt_db_k: float
    c_n0_db_hz: float
    
    # Data rate & performance
    target_data_rate_kbps: float
    eb_n0_received_db: float
    eb_n0_required_db: float
    link_margin_db: float
    is_link_closed: bool
    max_achievable_data_rate_kbps: float


def calculate_dish_gain_dbi(diameter_m: float, frequency_hz: float, efficiency: float = 0.55) -> float:
    """Calculate parabolic dish antenna gain in dBi."""
    if diameter_m <= 0:
        return 0.0
    wavelength = SPEED_OF_LIGHT_M_S / frequency_hz
    # G = efficiency * (pi * D / lambda)^2
    g_linear = efficiency * ((math.pi * diameter_m / wavelength) ** 2)
    return 10.0 * math.log10(max(1.0, g_linear))


def calculate_link_budget(
    frequency_band: str = "X-Band",
    tx_power_w: float = 15.0,  # 15W transmitter
    antenna_type: str = "Parabolic Dish",
    dish_diameter_m: float = 0.5,  # 50cm high-gain dish on lander
    custom_gain_dbi: Optional[float] = None,
    distance_km: float = 384400.0,
    target_data_rate_kbps: float = 256.0,  # 256 kbps science telemetry
    dsn_station_type: str = "34m BWG",  # '34m BWG' or '70m'
    eb_n0_required_db: float = 3.0,  # LDPC rate 1/2 threshold
    required_margin_db: float = 3.0,
) -> LinkBudgetResult:
    """Compute complete Direct-to-Earth RF downlink communications budget."""
    band_info = RF_BANDS.get(frequency_band, RF_BANDS["X-Band"])
    freq_hz = band_info["frequency_hz"]
    wavelength_m = SPEED_OF_LIGHT_M_S / freq_hz

    # Transmit power in dBW
    tx_power_w = max(0.1, tx_power_w)
    tx_power_dbw = 10.0 * math.log10(tx_power_w)

    # Antenna gain
    if antenna_type == "Parabolic Dish" and dish_diameter_m is not None:
        tx_gain_dbi = calculate_dish_gain_dbi(dish_diameter_m, freq_hz)
    elif custom_gain_dbi is not None:
        tx_gain_dbi = custom_gain_dbi
    else:
        # Patch / low gain antenna default
        tx_gain_dbi = 6.0

    tx_line_loss_db = 1.0
    tx_pointing_loss_db = 0.8 if antenna_type == "Parabolic Dish" else 0.2

    # EIRP = P_tx + G_tx - L_tx
    eirp_dbw = tx_power_dbw + tx_gain_dbi - tx_line_loss_db

    # Free Space Path Loss: FSPL = 20*log10(4*pi*d / lambda)
    distance_m = distance_km * 1000.0
    fspl_db = 20.0 * math.log10(4.0 * math.pi * distance_m / wavelength_m)

    # Atmospheric loss
    atm_loss_db = band_info.get("atm_loss_nominal_db", 0.1)

    total_path_loss = fspl_db + atm_loss_db + tx_pointing_loss_db

    # Receiver G/T
    if "70m" in dsn_station_type:
        rx_gt = band_info["dsn_70m_gt_db_k"]
    else:
        rx_gt = band_info["dsn_34m_gt_db_k"]

    # Boltzmann in dBW/(Hz*K)
    k_boltzmann_db = 10.0 * math.log10(BOLTZMANN_CONSTANT)  # -228.60 dBW/Hz/K

    # Carrier-to-Noise spectral density C/N0 (dB-Hz)
    # C/N0 = EIRP - Total_Path_Loss + (G/T) - 10*log10(k)
    c_n0_db_hz = eirp_dbw - total_path_loss + rx_gt - k_boltzmann_db

    # For given target data rate
    target_data_rate_bps = target_data_rate_kbps * 1000.0
    rate_db_hz = 10.0 * math.log10(max(1.0, target_data_rate_bps))

    # Eb/N0 = C/N0 - 10*log10(Rb)
    eb_n0_received = c_n0_db_hz - rate_db_hz
    link_margin_db = eb_n0_received - eb_n0_required_db
    is_closed = link_margin_db >= required_margin_db

    # Maximum achievable data rate with required margin:
    # max_rate_db = C/N0 - (Eb/N0_req + required_margin)
    max_rate_db = c_n0_db_hz - (eb_n0_required_db + required_margin_db)
    max_rate_bps = 10.0 ** (max_rate_db / 10.0)
    max_rate_kbps = max_rate_bps / 1000.0

    light_time_s = distance_m / SPEED_OF_LIGHT_M_S

    return LinkBudgetResult(
        frequency_band=frequency_band,
        frequency_hz=freq_hz,
        wavelength_m=round(wavelength_m, 4),
        distance_km=round(distance_km, 1),
        light_time_seconds=round(light_time_s, 4),
        tx_power_w=tx_power_w,
        tx_power_dbw=round(tx_power_dbw, 2),
        antenna_type=antenna_type,
        dish_diameter_m=dish_diameter_m,
        tx_antenna_gain_dbi=round(tx_gain_dbi, 2),
        tx_line_loss_db=round(tx_line_loss_db, 2),
        tx_pointing_loss_db=round(tx_pointing_loss_db, 2),
        eirp_dbw=round(eirp_dbw, 2),
        fspl_db=round(fspl_db, 2),
        atm_loss_db=round(atm_loss_db, 2),
        total_path_loss_db=round(total_path_loss, 2),
        dsn_station_type=dsn_station_type,
        rx_gt_db_k=round(rx_gt, 2),
        c_n0_db_hz=round(c_n0_db_hz, 2),
        target_data_rate_kbps=target_data_rate_kbps,
        eb_n0_received_db=round(eb_n0_received, 2),
        eb_n0_required_db=round(eb_n0_required_db, 2),
        link_margin_db=round(link_margin_db, 2),
        is_link_closed=is_closed,
        max_achievable_data_rate_kbps=round(max_rate_kbps, 1),
    )
