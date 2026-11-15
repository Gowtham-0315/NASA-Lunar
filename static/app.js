/**
 * Lunar Landing Site Intelligence Platform - Interactive Application Controller
 * Seamlessly integrates NASA Moon Trek, LROC QuickMap, JPL Horizons API, and CSA Exploration
 */

// Global State
let currentSites = [];
let selectedSite = null;
let currentSimulationData = null;
let leafletMap = null;
let siteMarkers = {};
let customPin = null;

// Chart Instances
let chartElevations = null;
let chartFlux = null;
let chartPolarHorizon = null;
let chartRadar = null;
let chartPareto = null;

document.addEventListener("DOMContentLoaded", () => {
    initNavigationTabs();
    initLeafletMap();
    initEventListeners();
    loadSites();
    loadCsaOverview();
    loadSavedSitesFromDb();
});

/* -------------------------------------------------------------
 * 1. Navigation Tabs
 * ----------------------------------------------------------- */
function initNavigationTabs() {
    const tabButtons = document.querySelectorAll(".tab-btn");
    tabButtons.forEach(btn => {
        btn.addEventListener("click", () => {
            tabButtons.forEach(b => b.classList.remove("active"));
            document.querySelectorAll(".tab-panel").forEach(p => p.classList.remove("active"));
            
            btn.classList.add("active");
            const targetId = btn.getAttribute("data-tab");
            const targetPanel = document.getElementById(targetId);
            if (targetPanel) {
                targetPanel.classList.add("active");
                if (targetId === "tab-map" && leafletMap) {
                    setTimeout(() => leafletMap.invalidateSize(), 100);
                }
                if (targetId === "tab-mcda" && !chartRadar) {
                    runMcdaComparison();
                }
            }
        });
    });
}

/* -------------------------------------------------------------
 * 2. Leaflet Lunar Map Integration (NASA Moon Trek Tiles)
 * ----------------------------------------------------------- */
function initLeafletMap() {
    // Standard Simple or Equirectangular projection for lunar surface
    leafletMap = L.map("lunar-map", {
        center: [-85.0, 50.0],
        zoom: 3,
        minZoom: 1,
        maxZoom: 8,
        attributionControl: false
    });

    // NASA Moon Trek LRO WAC Global Mosaic WMTS Tile Layer
    const moonTrekTileUrl = "https://trek.nasa.gov/tiles/Moon/EQ/LRO_WAC_Mosaic_Global_303ppd/1.0.0//default/default028mm/{z}/{y}/{x}.jpg";

    const baseTileLayer = L.tileLayer(moonTrekTileUrl, {
        maxZoom: 8,
        tms: false,
        noWrap: false,
        errorTileUrl: "https://cartocdn-gusc.global.ssl.fastly.net/openaerialmap/0/0/0.png"
    });
    baseTileLayer.addTo(leafletMap);

    // Map Click Handler: Pick any arbitrary coordinates on lunar surface
    leafletMap.on("click", (e) => {
        const lat = e.latlng.lat;
        const lon = (e.latlng.lng % 360 + 360) % 360; // 0 to 360 east positive
        handleMapCoordinateClick(lat, lon);
    });

    leafletMap.on("mousemove", (e) => {
        const lat = e.latlng.lat.toFixed(4);
        const lon = ((e.latlng.lng % 360 + 360) % 360).toFixed(4);
        const coordsSpan = document.getElementById("cursor-coords");
        if (coordsSpan) {
            coordsSpan.innerText = `Lat: ${lat}°, Lon: ${lon}°`;
        }
    });

    // Map Focus Presets
    document.querySelectorAll(".pill-btn[data-focus]").forEach(pill => {
        pill.addEventListener("click", () => {
            document.querySelectorAll(".pill-btn[data-focus]").forEach(p => p.classList.remove("active"));
            pill.classList.add("active");
            const focus = pill.getAttribute("data-focus");
            if (focus === "south-pole") {
                leafletMap.setView([-85.0, 45.0], 4);
            } else if (focus === "equatorial") {
                leafletMap.setView([0.0, 25.0], 3);
            } else {
                leafletMap.setView([0.0, 0.0], 2);
            }
        });
    });
}

function handleMapCoordinateClick(lat, lon) {
    if (customPin) {
        leafletMap.removeLayer(customPin);
    }
    customPin = L.marker([lat, lon], {
        icon: L.divIcon({
            className: "custom-map-pin",
            html: "<div style='font-size:22px; filter:drop-shadow(0 0 6px #f59e0b);'>📍</div>",
            iconSize: [24, 24],
            iconAnchor: [12, 22]
        })
    }).addTo(leafletMap);

    customPin.bindPopup(`
        <div style="font-family:sans-serif; font-size:12px; color:#1e293b;">
            <strong>Custom Lunar Point</strong><br>
            Lat: ${lat.toFixed(4)}°, Lon: ${lon.toFixed(4)}°<br>
            <button onclick="evaluateCustomCoordinates(${lat}, ${lon})" style="margin-top:6px; background:#2563eb; color:#fff; border:none; padding:4px 8px; border-radius:4px; cursor:pointer;">
                Analyze This Point
            </button>
        </div>
    `).openPopup();
}

window.evaluateCustomCoordinates = function(lat, lon) {
    document.getElementById("selected-coords").innerText = `${lat.toFixed(4)}°, ${lon.toFixed(4)}°`;
    document.getElementById("selected-elev").innerText = "0 m (Spherical Datum)";
    
    const startUtc = document.getElementById("start-utc").value + ":00Z";
    const endUtc = document.getElementById("end-utc").value + ":00Z";
    const stepSeconds = parseFloat(document.getElementById("step-select").value);
    const mastHeight = parseFloat(document.getElementById("mast-height").value);

    fetch("/api/evaluate-custom", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            latitude_deg: lat,
            longitude_deg: lon,
            elevation_m: 0.0,
            site_name: `Point (${lat.toFixed(2)}°, ${lon.toFixed(2)}°)`,
            start_utc: startUtc,
            end_utc: endUtc,
            step_seconds: stepSeconds,
            antenna_mast_height_m: mastHeight
        })
    })
    .then(r => r.json())
    .then(data => {
        applySimulationResults(data);
    })
    .catch(err => alert("Evaluation failed: " + err));
};

/* -------------------------------------------------------------
 * 3. Sites Loading & Markers
 * ----------------------------------------------------------- */
function loadSites() {
    fetch("/api/sites")
        .then(r => r.json())
        .then(data => {
            currentSites = data.sites;
            populateSiteDropdown();
            renderMapMarkers();
            if (currentSites.length > 0) {
                selectSite(currentSites[0].site_id);
                runSimulation();
            }
        })
        .catch(err => console.error("Error loading sites:", err));
}

function populateSiteDropdown() {
    const select = document.getElementById("site-select");
    select.innerHTML = "";

    const groups = {
        "Canadian Space Agency (CSA) Targets": [],
        "NASA Artemis III Candidate Regions": [],
        "Historic & Robotic Landers": []
    };

    currentSites.forEach(s => {
        if (s.site_id.startsWith("CSA_")) {
            groups["Canadian Space Agency (CSA) Targets"].push(s);
        } else if (s.region.includes("South Pole") && !s.site_id.startsWith("CHANDRA")) {
            groups["NASA Artemis III Candidate Regions"].push(s);
        } else {
            groups["Historic & Robotic Landers"].push(s);
        }
    });

    for (const [groupName, sites] of Object.entries(groups)) {
        if (sites.length === 0) continue;
        const optGroup = document.createElement("optgroup");
        optGroup.label = groupName;
        sites.forEach(s => {
            const opt = document.createElement("option");
            opt.value = s.site_id;
            opt.textContent = `${s.name} (${s.site_id})`;
            optGroup.appendChild(opt);
        });
        select.appendChild(optGroup);
    }

    select.addEventListener("change", (e) => {
        selectSite(e.target.value);
        runSimulation();
    });
}

function renderMapMarkers() {
    currentSites.forEach(s => {
        const isCsa = s.site_id.startsWith("CSA_");
        const isArtemis = s.region.includes("South Pole") && !isCsa;
        
        let markerIconHtml = "<div style='font-size:18px;'>📍</div>";
        if (isCsa) {
            markerIconHtml = "<div style='font-size:20px; filter:drop-shadow(0 0 8px #ef4444);'>🍁</div>";
        } else if (isArtemis) {
            markerIconHtml = "<div style='font-size:18px; filter:drop-shadow(0 0 6px #3b82f6);'>🎯</div>";
        }

        const marker = L.marker([s.latitude_deg, s.longitude_deg], {
            icon: L.divIcon({
                className: "lunar-site-marker",
                html: markerIconHtml,
                iconSize: [22, 22],
                iconAnchor: [11, 20]
            })
        }).addTo(leafletMap);

        marker.bindPopup(`
            <div style="font-family:sans-serif; font-size:12px; color:#0f172a; max-width:220px;">
                <strong style="color:#1e3a8a;">${s.name}</strong><br>
                <span style="font-size:11px; color:#475569;">Region: ${s.region}</span><br>
                <span>Lat: ${s.latitude_deg.toFixed(2)}°, Lon: ${s.longitude_deg.toFixed(2)}°</span><br>
                <div style="margin-top:6px; display:flex; gap:6px;">
                    <button onclick="window.selectAndSimulate('${s.site_id}')" style="background:#2563eb; color:#fff; border:none; padding:4px 8px; border-radius:4px; cursor:pointer;">
                        Select
                    </button>
                    <a href="${s.quickmap_url}" target="_blank" style="background:#4338ca; color:#fff; text-decoration:none; padding:4px 6px; border-radius:4px; font-size:11px;">
                        QuickMap ↗
                    </a>
                </div>
            </div>
        `);

        siteMarkers[s.site_id] = marker;
    });
}

window.selectAndSimulate = function(siteId) {
    document.getElementById("site-select").value = siteId;
    selectSite(siteId);
    runSimulation();
};

function selectSite(siteId) {
    selectedSite = currentSites.find(s => s.site_id === siteId);
    if (!selectedSite) return;

    // Update quick info
    document.getElementById("info-region").innerText = selectedSite.region;
    document.getElementById("info-coords").innerText = `${selectedSite.latitude_deg.toFixed(2)}°, ${selectedSite.longitude_deg.toFixed(2)}°`;
    document.getElementById("info-elev").innerText = `${selectedSite.elevation_m} m`;
    document.getElementById("info-slope").innerText = `${selectedSite.mean_slope_deg.toFixed(1)}°`;

    document.getElementById("selected-coords").innerText = `${selectedSite.latitude_deg.toFixed(4)}°, ${selectedSite.longitude_deg.toFixed(4)}°`;
    document.getElementById("selected-elev").innerText = `${selectedSite.elevation_m} m`;

    // Deep links
    document.getElementById("link-quickmap").href = selectedSite.quickmap_url;
    document.getElementById("link-moontrek").href = selectedSite.moon_trek_url;

    // Center map
    if (leafletMap) {
        leafletMap.panTo([selectedSite.latitude_deg, selectedSite.longitude_deg]);
        if (siteMarkers[siteId]) {
            siteMarkers[siteId].openPopup();
        }
    }
}

/* -------------------------------------------------------------
 * 4. Simulation Execution & Visualization
 * ----------------------------------------------------------- */
function initEventListeners() {
    document.getElementById("btn-run-sim").addEventListener("click", runSimulation);

    // DSN Link budget sliders
    document.getElementById("tx-power").addEventListener("input", (e) => {
        document.getElementById("tx-power-val").innerText = e.target.value;
        runLinkBudgetCalc();
    });
    document.getElementById("dish-diam").addEventListener("input", (e) => {
        document.getElementById("dish-diam-val").innerText = e.target.value;
        runLinkBudgetCalc();
    });
    document.getElementById("rf-band").addEventListener("change", runLinkBudgetCalc);
    document.getElementById("dsn-dish").addEventListener("change", runLinkBudgetCalc);
    document.getElementById("target-rate").addEventListener("input", runLinkBudgetCalc);

    // MCDA Recalculate
    document.getElementById("btn-recalculate-mcda").addEventListener("click", runMcdaComparison);
    document.querySelectorAll(".weight-input").forEach(slider => {
        slider.addEventListener("input", () => {
            const valSpan = document.getElementById(slider.id + "-val");
            if (valSpan) valSpan.innerText = slider.value + "%";
        });
    });

    // JPL Horizons live query
    document.getElementById("btn-hz-query").addEventListener("click", runHorizonsVerification);

    // Exports
    document.getElementById("btn-export-dossier").addEventListener("click", () => {
        if (!selectedSite) return;
        const startUtc = document.getElementById("start-utc").value + ":00Z";
        const endUtc = document.getElementById("end-utc").value + ":00Z";
        const step = parseFloat(document.getElementById("step-select").value);
        const mast = parseFloat(document.getElementById("mast-height").value);

        fetch("/api/export/report", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                site_id: selectedSite.site_id,
                start_utc: startUtc,
                end_utc: endUtc,
                step_seconds: step,
                antenna_mast_height_m: mast
            })
        })
        .then(r => r.text())
        .then(html => {
            const win = window.open("", "_blank");
            win.document.write(html);
            win.document.close();
        });
    });

    document.getElementById("btn-export-csv").addEventListener("click", () => {
        if (!selectedSite) return;
        const startUtc = document.getElementById("start-utc").value + ":00Z";
        const endUtc = document.getElementById("end-utc").value + ":00Z";
        const step = parseFloat(document.getElementById("step-select").value);
        const mast = parseFloat(document.getElementById("mast-height").value);

        fetch("/api/export/csv", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                site_id: selectedSite.site_id,
                start_utc: startUtc,
                end_utc: endUtc,
                step_seconds: step,
                antenna_mast_height_m: mast
            })
        })
        .then(r => r.blob())
        .then(blob => {
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = `${selectedSite.site_id}_lunar_simulation.csv`;
            document.body.appendChild(a);
            a.click();
            a.remove();
        });
    });
}

function runSimulation() {
    if (!selectedSite) return;

    const startUtc = document.getElementById("start-utc").value + ":00Z";
    const endUtc = document.getElementById("end-utc").value + ":00Z";
    const stepSeconds = parseFloat(document.getElementById("step-select").value);
    const mastHeight = parseFloat(document.getElementById("mast-height").value);

    fetch("/api/evaluate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            site_id: selectedSite.site_id,
            start_utc: startUtc,
            end_utc: endUtc,
            step_seconds: stepSeconds,
            antenna_mast_height_m: mastHeight
        })
    })
    .then(r => {
        if (!r.ok) throw new Error("Simulation endpoint error " + r.status);
        return r.json();
    })
    .then(data => {
        applySimulationResults(data);
    })
    .catch(err => {
        console.error("Simulation failed:", err);
    });
}

function applySimulationResults(data) {
    currentSimulationData = data;
    const summary = data.summary;
    const samples = data.samples;
    const horizon = data.horizon_mask;
    const csa = data.csa_compliance;

    // Update Footer Stat Cards
    document.getElementById("card-sunlight").innerText = `${(summary.sunlight_fraction * 100).toFixed(1)}%`;
    document.getElementById("card-sunlight-sub").innerText = `${summary.sunlight_duration_hours}h (${summary.longest_continuous_sunlight_hours}h continuous)`;

    document.getElementById("card-earth").innerText = `${(summary.earth_los_fraction * 100).toFixed(1)}%`;
    document.getElementById("card-earth-sub").innerText = `${summary.earth_los_duration_hours}h LOS (${summary.longest_continuous_earth_los_hours}h continuous)`;

    document.getElementById("card-windows").innerText = `${summary.touchdown_windows.length} Window(s)`;
    document.getElementById("card-windows-sub").innerText = `${summary.total_landing_window_hours}h total nominal duration`;

    // Render Elevation vs Time Chart
    renderElevationChart(samples);

    // Render Incident Flux Chart
    renderFluxChart(samples);

    // Render Touchdown Windows Table
    renderWindowsTable(summary.touchdown_windows);

    // Render 360 Polar Horizon Mask
    renderPolarHorizonChart(horizon, samples);

    // Update Horizon Mask Obstruction Metrics
    document.getElementById("mask-peak-el").innerText = `${horizon.max_obstruction_deg}°`;
    document.getElementById("mask-min-el").innerText = `${horizon.min_obstruction_deg}°`;
    document.getElementById("mask-mean-el").innerText = `${horizon.mean_obstruction_deg}°`;

    // Update DSN stations tracking based on latest sample
    if (samples.length > 0) {
        const latest = samples[0];
        updateDsnBadges(latest.active_dsn_stations);
    }

    // Update CSA Compliance Card
    updateCsaComplianceCard(csa);

    // Update Link Budget
    runLinkBudgetCalc();
}

function renderElevationChart(samples) {
    const ctx = document.getElementById("chart-elevations").getContext("2d");
    const labels = samples.map(s => s.timestamp_utc.replace("T", " ").substring(5, 16));
    const sunEls = samples.map(s => s.sun_elevation_deg);
    const earthEls = samples.map(s => s.earth_effective_elevation_deg);

    if (chartElevations) chartElevations.destroy();

    chartElevations = new Chart(ctx, {
        type: "line",
        data: {
            labels: labels,
            datasets: [
                {
                    label: "Sun Elevation (°)",
                    data: sunEls,
                    borderColor: "#f59e0b",
                    backgroundColor: "rgba(245, 158, 11, 0.1)",
                    borderWidth: 2,
                    tension: 0.1,
                    pointRadius: 0
                },
                {
                    label: "Earth Elevation (°)",
                    data: earthEls,
                    borderColor: "#06b6d4",
                    backgroundColor: "rgba(6, 182, 212, 0.1)",
                    borderWidth: 2,
                    tension: 0.1,
                    pointRadius: 0
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: { mode: "index", intersect: false },
            scales: {
                x: {
                    grid: { color: "rgba(255, 255, 255, 0.05)" },
                    ticks: { color: "#94a3b8", maxTicksLimit: 12 }
                },
                y: {
                    grid: { color: "rgba(255, 255, 255, 0.08)" },
                    ticks: { color: "#cbd5e1" },
                    title: { display: true, text: "Elevation Angle Above Local Horizon (°)", color: "#94a3b8" }
                }
            },
            plugins: {
                legend: { labels: { color: "#f8fafc" } },
                tooltip: {
                    callbacks: {
                        afterBody: (context) => {
                            const idx = context[0].dataIndex;
                            const s = samples[idx];
                            return [
                                `Sun Lit: ${s.is_lit ? 'YES' : 'NO'} (${(s.sun_disc_fraction*100).toFixed(0)}% disc)`,
                                `DSN Stations: ${s.active_dsn_stations.join(', ') || 'None'}`
                            ];
                        }
                    }
                }
            }
        }
    });
}

function renderFluxChart(samples) {
    const ctx = document.getElementById("chart-flux").getContext("2d");
    const labels = samples.map(s => s.timestamp_utc.replace("T", " ").substring(5, 16));
    const fluxes = samples.map(s => s.effective_solar_flux_w_m2);

    if (chartFlux) chartFlux.destroy();

    chartFlux = new Chart(ctx, {
        type: "line",
        data: {
            labels: labels,
            datasets: [{
                label: "Incident Solar Irradiance (W/m²)",
                data: fluxes,
                borderColor: "#10b981",
                backgroundColor: "rgba(16, 185, 129, 0.15)",
                fill: true,
                borderWidth: 1.5,
                pointRadius: 0
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: { ticks: { color: "#94a3b8", maxTicksLimit: 8 }, grid: { display: false } },
                y: {
                    ticks: { color: "#cbd5e1" },
                    title: { display: true, text: "Incident Flux (W/m²)", color: "#94a3b8" }
                }
            },
            plugins: {
                legend: { labels: { color: "#f8fafc" } }
            }
        }
    });
}

function renderWindowsTable(windows) {
    const tbody = document.querySelector("#windows-table tbody");
    tbody.innerHTML = "";

    if (!windows || windows.length === 0) {
        tbody.innerHTML = "<tr><td colspan='6' style='text-align:center; color:#94a3b8;'>No nominal landing windows found in this mission period.</td></tr>";
        return;
    }

    windows.forEach(w => {
        const tr = document.createElement("tr");
        tr.innerHTML = `
            <td><strong>${w.start_time_utc.replace("T", " ")}</strong></td>
            <td><strong>${w.end_time_utc.replace("T", " ")}</strong></td>
            <td class="highlight-gold">${w.duration_hours.toFixed(1)} hrs</td>
            <td>${w.avg_sun_elevation_deg.toFixed(1)}°</td>
            <td>${w.avg_earth_elevation_deg.toFixed(1)}°</td>
            <td>${w.active_dsn_stations.join(", ") || "None"}</td>
        `;
        tbody.appendChild(tr);
    });
}

function renderPolarHorizonChart(horizon, samples) {
    const ctx = document.getElementById("chart-polar-horizon").getContext("2d");
    
    // Polar radar: labels are azimuths 0° to 360°
    const labels = horizon.azimuths_deg.map(az => `${az.toFixed(0)}°`);
    const horizonEls = horizon.horizon_elevations_deg;

    // Sample Sun and Earth azimuths mapped to nearest bin
    const sunPoints = new Array(labels.length).fill(null);
    const earthPoints = new Array(labels.length).fill(null);

    samples.forEach(s => {
        const azIdx = Math.round((s.sun_azimuth_deg % 360) / (360 / labels.length)) % labels.length;
        sunPoints[azIdx] = Math.max(0, s.sun_elevation_deg);

        const eAzIdx = Math.round((s.earth_azimuth_deg % 360) / (360 / labels.length)) % labels.length;
        earthPoints[eAzIdx] = Math.max(0, s.earth_effective_elevation_deg);
    });

    if (chartPolarHorizon) chartPolarHorizon.destroy();

    chartPolarHorizon = new Chart(ctx, {
        type: "radar",
        data: {
            labels: labels,
            datasets: [
                {
                    label: "Crater Rim Horizon Obstruction (°)",
                    data: horizonEls,
                    borderColor: "#ef4444",
                    backgroundColor: "rgba(239, 68, 68, 0.25)",
                    borderWidth: 2,
                    pointRadius: 0
                },
                {
                    label: "Sun Elevation Track (°)",
                    data: sunPoints,
                    borderColor: "#f59e0b",
                    backgroundColor: "transparent",
                    borderWidth: 3,
                    pointRadius: 3,
                    pointBackgroundColor: "#f59e0b"
                },
                {
                    label: "Earth Elevation Track (°)",
                    data: earthPoints,
                    borderColor: "#06b6d4",
                    backgroundColor: "transparent",
                    borderWidth: 3,
                    pointRadius: 3,
                    pointBackgroundColor: "#06b6d4"
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                r: {
                    angleLines: { color: "rgba(255, 255, 255, 0.1)" },
                    grid: { color: "rgba(255, 255, 255, 0.1)" },
                    pointLabels: { color: "#94a3b8", font: { size: 10 } },
                    ticks: { color: "#cbd5e1", backdropColor: "transparent" },
                    min: 0,
                    suggestedMax: 12
                }
            },
            plugins: {
                legend: { labels: { color: "#f8fafc" } }
            }
        }
    });
}

function updateDsnBadges(activeStations) {
    const stations = ["goldstone", "madrid", "canberra"];
    stations.forEach(s => {
        const badge = document.getElementById(`dsn-${s}`);
        const elSpan = document.getElementById(`el-${s}`);
        const isActive = activeStations.some(act => act.toLowerCase().includes(s));
        if (isActive) {
            badge.classList.add("active");
            elSpan.innerText = "Tracking Status: ACTIVE CONTACT (LOS > 6°)";
            elSpan.style.color = "var(--accent-emerald)";
        } else {
            badge.classList.remove("active");
            elSpan.innerText = "Tracking Status: BELOW HORIZON";
            elSpan.style.color = "var(--text-muted)";
        }
    });
}

function runLinkBudgetCalc() {
    const band = document.getElementById("rf-band").value;
    const power = parseFloat(document.getElementById("tx-power").value);
    const dishDiam = parseFloat(document.getElementById("dish-diam").value);
    const dsnDish = document.getElementById("dsn-dish").value;
    const targetRate = parseFloat(document.getElementById("target-rate").value);

    fetch("/api/link-budget", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            frequency_band: band,
            tx_power_w: power,
            antenna_type: "Parabolic Dish",
            dish_diameter_m: dishDiam,
            target_data_rate_kbps: targetRate,
            dsn_station_type: dsnDish
        })
    })
    .then(r => r.json())
    .then(res => {
        const box = document.getElementById("budget-status-box");
        const statusEl = document.getElementById("budget-margin-status");
        const marginEl = document.getElementById("budget-margin-db");
        const maxRateEl = document.getElementById("budget-max-rate");

        if (res.is_link_closed) {
            box.className = "result-box closed";
            statusEl.innerText = "LINK CLOSED (POSITIVE MARGIN)";
            statusEl.style.color = "var(--accent-emerald)";
        } else {
            box.className = "result-box margin-low";
            statusEl.innerText = "LINK DEFICIT (NEGATIVE MARGIN)";
            statusEl.style.color = "var(--accent-rose)";
        }

        marginEl.innerText = `${res.link_margin_db > 0 ? '+' : ''}${res.link_margin_db} dB Margin`;
        maxRateEl.innerText = `Max Achievable Rate: ${res.max_achievable_data_rate_kbps.toLocaleString()} kbps`;

        document.getElementById("rf-dist").innerText = `${res.distance_km.toLocaleString()} km (~${res.light_time_seconds} s)`;
        document.getElementById("rf-tx-gain").innerText = `${res.tx_antenna_gain_dbi} dBi`;
        document.getElementById("rf-eirp").innerText = `${res.eirp_dbw} dBW`;
        document.getElementById("rf-fspl").innerText = `${res.fspl_db} dB`;
        document.getElementById("rf-gt").innerText = `${res.rx_gt_db_k} dB/K`;
        document.getElementById("rf-cn0").innerText = `${res.c_n0_db_hz} dB-Hz`;
        document.getElementById("rf-ebn0").innerText = `${res.eb_n0_received_db} dB (Req: ${res.eb_n0_required_db} dB)`;
    });
}

/* -------------------------------------------------------------
 * 5. MCDA Comparison & Sensitivity
 * ----------------------------------------------------------- */
function runMcdaComparison() {
    const siteIds = currentSites.slice(0, 8).map(s => s.site_id);
    const startUtc = document.getElementById("start-utc").value + ":00Z";
    const endUtc = document.getElementById("end-utc").value + ":00Z";

    const customWeights = {
        "sunlight_fraction": parseFloat(document.getElementById("w-sun").value) / 100.0,
        "longest_continuous_sunlight": parseFloat(document.getElementById("w-litsun").value) / 100.0,
        "earth_los_fraction": parseFloat(document.getElementById("w-earth").value) / 100.0,
        "co_visibility_fraction": parseFloat(document.getElementById("w-covis").value) / 100.0,
        "slope_safety": parseFloat(document.getElementById("w-slope").value) / 100.0,
        "science_priority": parseFloat(document.getElementById("w-sci").value) / 100.0,
    };

    fetch("/api/compare", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            site_ids: siteIds,
            start_utc: startUtc,
            end_utc: endUtc,
            step_seconds: 7200.0,
            weights: customWeights
        })
    })
    .then(r => r.json())
    .then(data => {
        renderMcdaTable(data.ranked_sites);
        renderMcdaRadar(data.ranked_sites.slice(0, 3));
        renderParetoScatter(data.ranked_sites);
    })
    .catch(err => console.error("MCDA calculation failed:", err));
}

function renderMcdaTable(rankedSites) {
    const tbody = document.querySelector("#mcda-table tbody");
    tbody.innerHTML = "";

    rankedSites.forEach(s => {
        const tr = document.createElement("tr");
        const paretoBadge = s.is_pareto_optimal 
            ? "<span style='color:#10b981; font-weight:700;'>★ Pareto Frontier</span>" 
            : "<span style='color:#64748b;'>Dominated</span>";

        tr.innerHTML = `
            <td><strong>#${s.rank}</strong></td>
            <td><strong style="color:#93c5fd;">${s.site_name}</strong></td>
            <td>${s.region}</td>
            <td class="highlight-gold" style="font-weight:700;">${s.wsm_score.toFixed(1)}</td>
            <td class="highlight-blue">${s.topsis_score.toFixed(1)}%</td>
            <td>${paretoBadge}</td>
            <td>${(s.sunlight_fraction*100).toFixed(0)}% (${s.longest_continuous_sunlight_hours.toFixed(0)}h)</td>
            <td>${(s.earth_los_fraction*100).toFixed(0)}%</td>
            <td>${s.mean_slope_deg.toFixed(1)}°</td>
            <td style="font-size:11px; max-width:240px;">${s.summary_verdict}</td>
        `;
        tbody.appendChild(tr);
    });
}

function renderMcdaRadar(topSites) {
    const ctx = document.getElementById("chart-mcda-radar").getContext("2d");
    const labels = ["Sun Availability", "Continuous Sunlight", "Direct Earth LOS", "Co-Visibility", "Slope Safety", "Volatiles Science"];

    const colors = [
        { border: "#3b82f6", bg: "rgba(59, 130, 246, 0.2)" },
        { border: "#10b981", bg: "rgba(16, 185, 129, 0.2)" },
        { border: "#f59e0b", bg: "rgba(245, 158, 11, 0.2)" }
    ];

    const datasets = topSites.map((s, idx) => ({
        label: `#${s.rank} ${s.site_name}`,
        data: [
            s.norm_scores.sunlight_fraction || 0,
            s.norm_scores.longest_continuous_sunlight || 0,
            s.norm_scores.earth_los_fraction || 0,
            s.norm_scores.co_visibility_fraction || 0,
            s.norm_scores.slope_safety || 0,
            s.norm_scores.science_priority || 0
        ],
        borderColor: colors[idx % 3].border,
        backgroundColor: colors[idx % 3].bg,
        borderWidth: 2
    }));

    if (chartRadar) chartRadar.destroy();

    chartRadar = new Chart(ctx, {
        type: "radar",
        data: { labels: labels, datasets: datasets },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                r: {
                    angleLines: { color: "rgba(255, 255, 255, 0.1)" },
                    grid: { color: "rgba(255, 255, 255, 0.1)" },
                    ticks: { display: false },
                    pointLabels: { color: "#cbd5e1", font: { size: 11 } },
                    min: 0,
                    max: 1
                }
            },
            plugins: {
                legend: { labels: { color: "#f8fafc" } }
            }
        }
    });
}

function renderParetoScatter(sites) {
    const ctx = document.getElementById("chart-pareto").getContext("2d");

    const paretoPoints = sites.filter(s => s.is_pareto_optimal).map(s => ({
        x: s.sunlight_fraction * 100,
        y: s.earth_los_fraction * 100,
        name: s.site_name
    }));

    const nonParetoPoints = sites.filter(s => !s.is_pareto_optimal).map(s => ({
        x: s.sunlight_fraction * 100,
        y: s.earth_los_fraction * 100,
        name: s.site_name
    }));

    if (chartPareto) chartPareto.destroy();

    chartPareto = new Chart(ctx, {
        type: "scatter",
        data: {
            datasets: [
                {
                    label: "Pareto Frontier (Non-Dominated)",
                    data: paretoPoints,
                    borderColor: "#10b981",
                    backgroundColor: "#10b981",
                    pointRadius: 6,
                    pointHoverRadius: 8
                },
                {
                    label: "Dominated Sites",
                    data: nonParetoPoints,
                    borderColor: "#64748b",
                    backgroundColor: "#64748b",
                    pointRadius: 5
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: {
                    title: { display: true, text: "Sunlight Availability (%)", color: "#94a3b8" },
                    ticks: { color: "#cbd5e1" },
                    grid: { color: "rgba(255, 255, 255, 0.05)" }
                },
                y: {
                    title: { display: true, text: "Direct Earth Line-of-Sight (%)", color: "#94a3b8" },
                    ticks: { color: "#cbd5e1" },
                    grid: { color: "rgba(255, 255, 255, 0.05)" }
                }
            },
            plugins: {
                tooltip: {
                    callbacks: {
                        label: (ctx) => `${ctx.raw.name}: Sun ${ctx.raw.x.toFixed(1)}%, Earth ${ctx.raw.y.toFixed(1)}%`
                    }
                },
                legend: { labels: { color: "#f8fafc" } }
            }
        }
    });
}

/* -------------------------------------------------------------
 * 6. Canadian Space Agency (CSA) Exploration Overview
 * ----------------------------------------------------------- */
function loadCsaOverview() {
    fetch("/api/csa-overview")
        .then(r => r.json())
        .then(data => {
            const container = document.getElementById("csa-payloads-container");
            container.innerHTML = "";

            data.rover_payloads.forEach(p => {
                const card = document.createElement("div");
                card.className = "payload-card";
                card.innerHTML = `
                    <h4>${p.name}</h4>
                    <div class="payload-lead">Lead: ${p.lead_institution} | Type: ${p.instrument_type}</div>
                    <div class="payload-desc">${p.description}</div>
                `;
                container.appendChild(card);
            });
        });
}

function updateCsaComplianceCard(compliance) {
    const grid = document.getElementById("csa-compliance-grid");
    if (!grid) return;

    grid.innerHTML = `
        <div class="stat-card">
            <span class="card-title">Slope Compliance</span>
            <span class="card-val ${compliance.slope_compliant ? 'highlight-green' : 'highlight-gold'}">${compliance.slope_deg.toFixed(1)}°</span>
            <span class="card-sub">Max limit: ${compliance.max_slope_limit_deg}°</span>
        </div>
        <div class="stat-card">
            <span class="card-title">Continuous Sunlight</span>
            <span class="card-val ${compliance.sunlight_compliant ? 'highlight-green' : 'highlight-gold'}">${compliance.continuous_lit_hours.toFixed(1)}h</span>
            <span class="card-sub">Min required: ${compliance.min_lit_hours_required}h</span>
        </div>
        <div class="stat-card">
            <span class="card-title">PSR Access Rating</span>
            <span class="card-val highlight-blue">${compliance.psr_access_rating}</span>
            <span class="card-sub">Volatile prospecting</span>
        </div>
        <div class="stat-card">
            <span class="card-title">CSA Science Score</span>
            <span class="card-val highlight-gold">${compliance.scientific_alignment_score.toFixed(0)}/100</span>
            <span class="card-sub">${compliance.is_compliant ? 'FULLY COMPLIANT' : 'CONDITIONALLY VIABLE'}</span>
        </div>
    `;
}

/* -------------------------------------------------------------
 * 7. JPL Horizons Live Ephemeris Verification
 * ----------------------------------------------------------- */
function runHorizonsVerification() {
    if (!selectedSite) return;

    const target = document.getElementById("hz-target").value;
    const epoch = document.getElementById("hz-epoch").value;
    const btn = document.getElementById("btn-hz-query");
    btn.disabled = true;
    btn.innerText = "Querying Horizons...";

    fetch("/api/horizons/verify", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            target: target,
            epoch_utc: epoch,
            site_id: selectedSite.site_id
        })
    })
    .then(r => r.json())
    .then(res => {
        btn.disabled = false;
        btn.innerText = "🛰️ Query JPL Horizons API";

        const box = document.getElementById("hz-result-box");
        box.classList.remove("hidden");

        document.getElementById("hz-status").innerText = res.status;
        document.getElementById("hz-internal-el").innerText = `${res.internal_elevation_deg}°`;
        document.getElementById("hz-remote-el").innerText = res.horizons_elevation_deg !== null ? `${res.horizons_elevation_deg}°` : "N/A";
        document.getElementById("hz-delta-el").innerText = res.delta_elevation_deg !== null ? `Δ ${res.delta_elevation_deg}°` : "--";

        document.getElementById("hz-internal-az").innerText = `${res.internal_azimuth_deg}°`;
        document.getElementById("hz-remote-az").innerText = res.horizons_azimuth_deg !== null ? `${res.horizons_azimuth_deg}°` : "N/A";
        document.getElementById("hz-delta-az").innerText = res.delta_azimuth_deg !== null ? `Δ ${res.delta_azimuth_deg}°` : "--";

        document.getElementById("hz-internal-dist").innerText = `${res.internal_distance_km.toLocaleString()} km`;
        document.getElementById("hz-remote-dist").innerText = res.horizons_range_km !== null ? `${res.horizons_range_km.toLocaleString()} km` : "N/A";
        document.getElementById("hz-delta-dist").innerText = res.delta_range_km !== null ? `Δ ${res.delta_range_km.toLocaleString()} km` : "--";

        document.getElementById("hz-notes").innerText = res.notes;
    })
    .catch(err => {
        btn.disabled = false;
        btn.innerText = "🛰️ Query JPL Horizons API";
        alert("Horizons query error: " + err);
    });
}

/* -------------------------------------------------------------
 * 8. SQLite Database Persistence (Saved Sites & Snapshots)
 * ----------------------------------------------------------- */
function loadSavedSitesFromDb() {
    fetch("/sites")
        .then(r => r.json())
        .then(data => {
            const sites = data.sites || [];
            const tbody = document.querySelector("#table-saved-sites tbody");
            if (!tbody) return;

            tbody.innerHTML = "";
            let totalSnaps = 0;

            if (sites.length === 0) {
                tbody.innerHTML = "<tr><td colspan='7' style='text-align:center; color:#94a3b8;'>No saved landing points in SQLite database yet.</td></tr>";
            } else {
                sites.forEach(s => {
                    totalSnaps += (s.assessment_count || 0);
                    const tr = document.createElement("tr");
                    tr.innerHTML = `
                        <td><strong>#${s.id}</strong></td>
                        <td><strong style="color:#93c5fd;">${s.name}</strong></td>
                        <td>${Number(s.latitude).toFixed(3)}°, ${Number(s.longitude).toFixed(3)}°</td>
                        <td style="font-size:11px; color:#94a3b8;">${s.created_at_utc ? s.created_at_utc.replace("T", " ").substring(0, 19) : "--"}</td>
                        <td><span class="highlight-gold">${s.assessment_count || 0}</span></td>
                        <td style="font-size:11px;">${s.last_assessed_at_utc ? s.last_assessed_at_utc.replace("T", " ").substring(0, 19) : "Never"}</td>
                        <td>
                            <button onclick="window.runAndSaveSnapshot(${s.id}, ${s.latitude}, ${s.longitude})" class="btn btn-secondary" style="padding:3px 8px; font-size:11px;">
                                📸 Snapshot
                            </button>
                        </td>
                    `;
                    tbody.appendChild(tr);
                });
            }

            const totalSitesEl = document.getElementById("db-total-sites");
            const totalSnapsEl = document.getElementById("db-total-snaps");
            if (totalSitesEl) totalSitesEl.innerText = `${sites.length} sites`;
            if (totalSnapsEl) totalSnapsEl.innerText = `${totalSnaps} snapshots`;
        })
        .catch(err => console.error("Error loading SQLite sites:", err));
}

window.runAndSaveSnapshot = function(siteId, lat, lon) {
    const timestampUtc = new Date().toISOString();
    fetch(`/sites/${siteId}/assessments`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ timestamp_utc: timestampUtc })
    })
    .then(r => r.json())
    .then(res => {
        alert(`Snapshot #${res.id} saved to SQLite successfully! Sun Lit: ${res.assessment.results[0].value.is_lit ? 'YES' : 'NO'}, Earth LOS: ${res.assessment.results[1].value.dte_los_available ? 'YES' : 'NO'}`);
        loadSavedSitesFromDb();
    })
    .catch(err => alert("Snapshot error: " + err));
};

const saveSiteForm = document.getElementById("form-save-site");
if (saveSiteForm) {
    saveSiteForm.addEventListener("submit", (e) => {
        e.preventDefault();
        const name = document.getElementById("db-site-name").value;
        const lat = parseFloat(document.getElementById("db-site-lat").value);
        const lon = parseFloat(document.getElementById("db-site-lon").value);

        fetch("/sites", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ name: name, latitude: lat, longitude: lon })
        })
        .then(r => r.json())
        .then(res => {
            alert(`Site "${res.name}" (ID #${res.id}) saved to SQLite database!`);
            document.getElementById("db-site-name").value = "";
            loadSavedSitesFromDb();
        })
        .catch(err => alert("Save site error: " + err));
    });
}
