

import { useEffect, useState } from "react";
import L from "leaflet";
import { CircleMarker, MapContainer, WMSTileLayer, useMap, useMapEvents } from "react-leaflet";
import { getBackendHealth, getSiteAssessment, createSite, getSites, saveAssessment } from "./services/api";
import "leaflet/dist/leaflet.css";
import "./App.css";

const navigation = [
  { id: "overview", icon: "⌂", label: "Overview" },
  { id: "explorer", icon: "◉", label: "Moon Explorer" },
  { id: "sites", icon: "◎", label: "Landing Sites" },
  { id: "comparison", icon: "⇄", label: "Comparison" },
  { id: "hazards", icon: "△", label: "Hazard Analysis" },
  { id: "resources", icon: "R", label: "Resources" },
  { id: "help", icon: "?", label: "Help" },
];

const metrics = [
  { label: "SUN ILLUMINATION", value: "MAP", unit: "SPICE-powered time-selected layer", icon: "☼" },
  { label: "EARTH VISIBILITY", value: "—", unit: "Geometry not evaluated", icon: "◌" },
  { label: "SURFACE TEMPERATURE", value: "—", unit: "Diviner data not connected", icon: "°" },
  { label: "TERRAIN & HAZARDS", value: "—", unit: "Relief map in Explorer; no safety score", icon: "△" },
];

function App() {
  
  const [activePage, setActivePage] = useState("overview");
  const [backendStatus, setBackendStatus] = useState("checking");


useEffect(() => {
  async function checkBackend() {
    try {
      const data = await getBackendHealth();

      setBackendStatus(
        data.status === "healthy" ? "online" : "offline"
      );
    } catch (error) {
      console.error("Backend connection failed:", error);
      setBackendStatus("offline");
    }
  }
  checkBackend();
  const intervalId = setInterval(checkBackend, 5000);
  return () => clearInterval(intervalId);}, []);
  const currentPage = navigation.find((item) => item.id === activePage);

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <img className="brand-symbol brand-logo" src="/llie-logo.png" alt="Lunar Landing Intelligence Engine" />
          <div>
            <h1>LUNAR<span>COMMAND</span></h1>
            <p>LANDING SITE NAVIGATOR</p>
          </div>
        </div>

        <div className="sidebar-label">WORKSPACE</div>

        <nav className="navigation">
          {navigation.map((item) => (
            <button
              key={item.id}
              className={`nav-item ${activePage === item.id ? "active" : ""}`}
              onClick={() => setActivePage(item.id)}
            >
              <span className="nav-icon">{item.icon}</span>
              <span>{item.label}</span>
              {activePage === item.id && <span className="active-indicator" />}
            </button>
          ))}
        </nav>

        <div className="sidebar-bottom">
          <div className="mission-card">
            <div className="mission-card-top">
              <span className="status-dot" />
              MISSION STATUS
            </div>
            <h3>System status</h3>
            <p>API connection and data availability are shown in the workspace.</p>
          </div>

          <div className="sidebar-footer">
            <span>SPACE APPS CHALLENGE</span>
            <span>GLOBAL LUNAR EXPLORATION</span>
          </div>
        </div>
      </aside>

      <main className="main-content">
        <header className="topbar">
          <div className="breadcrumb">
            <span>MISSION CENTER</span>
            <span className="breadcrumb-divider">/</span>
            <strong>{currentPage?.label.toUpperCase()}</strong>
          </div>

          <div className="topbar-right">
            <div className="live-status">
              <span className={`status-dot ${backendStatus}`} />
              {backendStatus === "checking"
                ? "CHECKING..."
                : backendStatus === "online"
                ? "SYSTEM ONLINE"
                : "SYSTEM OFFLINE"}
            </div>
            <div className="topbar-divider" />
            <div className="mission-code">LLSN / 2026</div>
          </div>
        </header>

        {activePage === "overview" ? (
          <Dashboard onOpenExplorer={() => setActivePage("explorer")} />
        ) : activePage === "sites" ? (
          <SavedSitesPage />
        ) : activePage === "resources" ? (
          <ResourcesPage />
        ) : activePage === "help" ? (
          <HelpPage />
        ) : (
          <SiteAssessmentPage page={currentPage?.label} />
        )}
      </main>
    </div>
  );
}

function Dashboard({ onOpenExplorer }) {
  const [sites, setSites] = useState([]);
  const [sitesLoading, setSitesLoading] = useState(true);
  useEffect(() => {
    getSites().then((response) => setSites(response.sites || []))
      .catch(() => setSites([]))
      .finally(() => setSitesLoading(false));
  }, []);
  return (
    <div className="page-content">
      <section className="welcome-section">
        <div>
          <div className="eyebrow">
            <span className="eyebrow-line" />
            GLOBAL LUNAR INTELLIGENCE
          </div>
          <h2>Explore the Moon.<br /><span>Find the landing site.</span></h2>
          <p className="welcome-description">
            An integrated view of lunar terrain, environmental conditions,
            visibility and potential landing hazards.
          </p>
        </div>

        <div className="date-display">
          <span>MISSION ENVIRONMENT</span>
          <strong>GLOBAL MOON</strong>
          <small>Choose a point in Moon Explorer</small>
        </div>
      </section>

      <section className="metrics-grid">
        {metrics.map((metric) => (
          <article className="metric-card" key={metric.label}>
            <div className="metric-top">
              <span>{metric.label}</span>
              <span className="metric-icon">{metric.icon}</span>
            </div>
            <div className="metric-value">{metric.value}</div>
            <div className="metric-unit">{metric.unit}</div>
          </article>
        ))}
      </section>

      <section className="workspace-grid">
        <article className="panel lunar-panel">
          <div className="panel-heading">
            <div>
              <div className="panel-kicker">PRIMARY VISUALIZATION</div>
              <h3>Lunar surface explorer</h3>
            </div>
            <span className="panel-tag">GLOBAL VIEW</span>
          </div>

          <div className="moon-stage">
            <div className="moon-orbit orbit-one" />
            <div className="moon-orbit orbit-two" />
            <div className="moon-glow" />
            <div className="moon-sphere">
              <div className="moon-craters" />
            </div>
            <div className="moon-caption">
              <span className="caption-dot" />
              LUNAR GLOBE ILLUSTRATION
            </div>
            <div className="map-overlay-label">
              <span>VISUALIZATION</span>
              <strong>ILLUSTRATION ONLY</strong>
            </div>
          </div>

          <div className="map-footer">
            <div>
              <span className="footer-label">COORDINATES</span>
              <strong>Select a location</strong>
            </div>
            <div>
              <span className="footer-label">DATA COVERAGE</span>
              <strong>Live map in Explorer</strong>
            </div>
            <button className="text-button" onClick={onOpenExplorer}>
              OPEN EXPLORER <span>→</span>
            </button>
          </div>
        </article>

        <article className="panel intelligence-panel">
          <div className="panel-heading">
            <div>
              <div className="panel-kicker">MISSION ANALYTICS</div>
              <h3>Site intelligence</h3>
            </div>
            <span className="subtle-icon">⌖</span>
          </div>

          <div className="intelligence-intro">
            Select a lunar location to inspect available environmental data.
          </div>

          {[
            ["01", "Solar illumination", "SPICE-powered map for selected time"],
            ["02", "Earth communication", "Earth visibility"],
            ["03", "Thermal conditions", "Temperature data"],
            ["04", "Surface safety", "Terrain and hazards"],
          ].map(([number, title, description]) => (
            <div className="intelligence-row" key={number}>
              <span className="intelligence-number">{number}</span>
              <div className="intelligence-copy">
                <strong>{title}</strong>
                <span>{description}</span>
              </div>
              <span className="pending-pill">{number === "01" ? "MAP LAYER" : "NOT EVALUATED"}</span>
            </div>
          ))}

          <div className="validation-note">
            Scientific outputs require validated data sources; no values are estimated.
          </div>
        </article>
      </section>

      <section className="bottom-grid">
        <article className="panel bottom-panel">
          <div className="panel-heading">
            <div>
              <div className="panel-kicker">EXPLORATION WORKSPACE</div>
              <h3>Landing site candidates</h3>
            </div>
            <span className="panel-tag">{sitesLoading ? "LOADING" : `${sites.length} SAVED`}</span>
          </div>
          {sitesLoading ? <div className="empty-state"><strong>Loading saved locations…</strong></div> : sites.length === 0 ? (
            <div className="empty-state">
              <div className="empty-icon">⌖</div>
              <strong>No landing sites saved</strong>
              <span>Inspect a location in Moon Explorer to save it to your workspace.</span>
            </div>
          ) : <div className="dashboard-sites-list">{sites.slice(0, 4).map((site) => (
            <div className="dashboard-site-row" key={site.id}>
              <div><strong>{site.name}</strong><span>{Number(site.latitude).toFixed(3)}° lat, {Number(site.longitude).toFixed(3)}° lon</span></div>
              <span>{site.assessment_count} checks</span>
            </div>
          ))}</div>}
        </article>

        <article className="panel bottom-panel">
          <div className="panel-heading">
            <div>
              <div className="panel-kicker">DATA PIPELINE</div>
              <h3>Module readiness</h3>
            </div>
            <span className="panel-tag">DATA AVAILABILITY</span>
          </div>

          <div className="pipeline-list">
            {[["Backend", "Connection status in header"], ["Solar illumination", "SPICE map in Explorer"], ["Terrain measurements", "Not calculated"], ["Thermal", "Diviner data unavailable"]].map(([item, status]) => (
              <div className="pipeline-row" key={item}>
                <span>{item}</span>
                <span className="pipeline-pending">{status}</span>
              </div>
            ))}
          </div>
        </article>
      </section>

      <footer className="page-footer">
        <span>LUNAR COMMAND <span className="footer-separator">/</span> SPACE APPS CHALLENGE</span>
        <span>DATA SOURCES AND SCIENTIFIC VALIDATION REQUIRED</span>
      </footer>
    </div>
  );
}

function ResourcesPage() {
  const resources = [
    ["LROC WAC lunar imagery", "Global LRO Wide Angle Camera mosaic streamed into Moon Explorer.", "https://wms.lroc.asu.edu/lroc/view_rdr/WAC_GLOBAL"],
    ["GLD100 terrain model", "WAC-derived global terrain product. The explorer displays shaded relief; point elevation and slope are not calculated.", "https://wms.lroc.asu.edu/lroc/view_rdr/WAC_GLD100"],
    ["Challenge brief", "NASA Space Apps challenge goals and context.", "https://www.spaceappschallenge.org/2026/challenges/lunar-landing-site-navigator/"],
    ["JPL Horizons", "Interactive ephemerides and official system manual; validate timescale and observer settings.", "https://ssd.jpl.nasa.gov/horizons/"],
    ["NAIF lunar SPICE data", "Lunar mission kernels; check frame definitions and time coverage before calculations.", "https://naif.jpl.nasa.gov/naif/data_lunar.html"],
    ["LRO PDS archive", "Mission archive, including LOLA, Diviner and LROC data collections.", "https://pds-geosciences.wustl.edu/missions/lro/default.htm"],
    ["LOLA archive", "Lunar Orbiter Laser Altimeter topography products and archive notes.", "https://pds-geosciences.wustl.edu/missions/lro/lola.htm"],
    ["Lunar coordinate guide", "NASA white paper on lunar reference systems and coordinate conventions.", "https://science.nasa.gov/wp-content/uploads/2024/01/luncoordwhitepaper-10-08.pdf"],
  ];
  return (
    <div className="page-content resource-page">
      <div className="eyebrow"><span className="eyebrow-line" /> DATA AND REFERENCES</div>
      <h2>Resources</h2>
      <p className="welcome-description">Moon Explorer streams LROC imagery and GLD100 shaded relief. Other links are scientific references; solar, terrain-measurement, and thermal calculations are not connected.</p>
      <div className="resource-grid">
        {resources.map(([title, description, url]) => (
          <article className="panel resource-card" key={title}>
            <div className="panel-kicker">REFERENCE SOURCE</div>
            <h3>{title}</h3><p>{description}</p>
            <a href={url} target="_blank" rel="noreferrer">Open official resource</a>
          </article>
        ))}
      </div>
      <div className="panel source-note"><strong>Data use</strong><span>Only the LROC imagery and GLD100 relief layers are fetched by the explorer. The other sources are reference links and are not queried by the application.</span></div>
    </div>
  );
}

function HelpPage() {
  return (
    <div className="page-content help-page">
      <div className="eyebrow"><span className="eyebrow-line" /> QUICK GUIDE</div>
      <h2>Help</h2>
      <div className="help-grid">
        <article className="panel help-card"><span className="help-number">01</span><h3>Explore a point</h3><p>Pan and zoom the live LROC Moon map, choose imagery or GLD100 terrain relief, and click the surface to set coordinates. Enter a name and observation time, then inspect the available results.</p></article>
        <article className="panel help-card"><span className="help-number">02</span><h3>Compare two points</h3><p>Submit two locations at the same time. Comparison currently reports data availability only; it does not rank sites or calculate visibility or safety.</p></article>
        <article className="panel help-card"><span className="help-number">03</span><h3>Find saved work</h3><p>Each successful check saves the named point and a timestamped status snapshot in the local SQLite database. Open Landing Sites to see saved points and snapshot counts.</p></article>
        <article className="panel help-card"><span className="help-number">04</span><h3>Read each state</h3><p>UNAVAILABLE means a required data source is not connected. NOT_EVALUATED means no validated calculation ran. Neither state means safe, unsafe, visible, or dark.</p></article>
      </div>
      <div className="panel source-note"><strong>Local API help</strong><span>Open the interactive FastAPI endpoint reference at <a href="http://127.0.0.1:8000/docs" target="_blank" rel="noreferrer">127.0.0.1:8000/docs</a>. The SQLite database is stored at backend/data/llsn.sqlite3 and is excluded from Git.</span></div>
    </div>
  );
}

function SavedSitesPage() {
  const [sites, setSites] = useState([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    getSites().then((response) => setSites(response.sites))
      .catch((requestError) => setError(requestError.message))
      .finally(() => setLoading(false));
  }, []);
  return (
    <div className="page-content saved-sites-page">
      <div className="eyebrow"><span className="eyebrow-line" /> SQLITE STORAGE</div>
      <h2>Landing Sites</h2>
      <p className="welcome-description">Saved coordinates and time-stamped assessment status snapshots from this app.</p>
      {loading && <p>Loading saved sites...</p>}
      {error && <p className="assessment-error">Could not load saved sites: {error}</p>}
      {!loading && !error && sites.length === 0 && <div className="panel empty-state"><strong>No saved points yet</strong><span>Check a point in Moon Explorer or Comparison to save it here.</span></div>}
      <div className="saved-sites-list">
        {sites.map((site) => (
          <article className="panel saved-site-card" key={site.id}>
            <div><div className="panel-kicker">SAVED POINT #{site.id}</div><h3>{site.name}</h3><p>{site.latitude} lat, {site.longitude} lon</p></div>
            <div className="saved-site-meta"><strong>{site.assessment_count} snapshots</strong><span>{site.last_assessed_at_utc ? `Last checked ${site.last_assessed_at_utc} UTC` : "Not assessed yet"}</span></div>
          </article>
        ))}
      </div>
    </div>
  );
}
function SiteAssessmentPage({ page }) {
  const [latitude, setLatitude] = useState("-89.5");
  const [longitude, setLongitude] = useState("0");
  const [siteName, setSiteName] = useState("Candidate A");
  const [secondSiteName, setSecondSiteName] = useState("Candidate B");
  const [assessmentTime, setAssessmentTime] = useState(() => {
    const now = new Date();
    now.setMinutes(now.getMinutes() - now.getTimezoneOffset());
    return now.toISOString().slice(0, 16);
  });
  const [secondLatitude, setSecondLatitude] = useState("-88.5");
  const [secondLongitude, setSecondLongitude] = useState("90");
  const [assessments, setAssessments] = useState([]);
  const [mapLayer, setMapLayer] = useState("imagery");
  const [mapStatus, setMapStatus] = useState("Loading LROC map tiles…");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const compare = page === "Comparison";
  const explorer = page === "Moon Explorer";

  async function analyzeSites(event) {
    event.preventDefault();
    setLoading(true);
    setError("");
    try {
      const timestampUtc = new Date(assessmentTime).toISOString();
      const first = getSiteAssessment(latitude, longitude, timestampUtc);
      const responses = compare
        ? await Promise.all([first, getSiteAssessment(secondLatitude, secondLongitude, timestampUtc)])
        : [await first];
      const points = compare
        ? [{ name: siteName, latitude, longitude }, { name: secondSiteName, latitude: secondLatitude, longitude: secondLongitude }]
        : [{ name: siteName, latitude, longitude }];
      const persisted = await Promise.all(responses.map(async (assessment, index) => {
        try {
          const point = points[index];
          const site = await createSite({ name: point.name, latitude: Number(point.latitude), longitude: Number(point.longitude) });
          await saveAssessment(site.id, timestampUtc);
          return { ...assessment, persistence_note: "Saved to local SQLite database." };
        } catch (saveError) {
          return { ...assessment, persistence_note: `Database save failed: ${saveError.message}` };
        }
      }));
      setAssessments(persisted);
    } catch (requestError) {
      setError(`Assessment service unavailable: ${requestError.message}`);
      setAssessments([]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="page-content assessment-page">
      <div className="eyebrow"><span className="eyebrow-line" /> SITE WORKSPACE</div>
      <h2>{page}</h2>
      <p className="welcome-description">
        {explorer
          ? "Select a point on the schematic lunar coordinate grid or enter coordinates. The grid is a coordinate aid, not surface imagery or terrain data."
          : "Enter lunar coordinates to retrieve the backend's verified capability states. Example coordinates are for interface demonstration only, not recommended sites."}
      </p>
      {explorer && <section className="explorer-map-panel panel">
        <div className="map-layer-controls" role="group" aria-label="Moon map layer">
          <button type="button" className={mapLayer === "imagery" ? "selected" : ""} onClick={() => { setMapLayer("imagery"); setMapStatus("Loading LROC imagery…"); }}>LROC imagery</button>
          <button type="button" className={mapLayer === "terrain" ? "selected" : ""} onClick={() => { setMapLayer("terrain"); setMapStatus("Loading GLD100 terrain relief…"); }}>Terrain relief</button>
          <button type="button" className={mapLayer === "illumination" ? "selected" : ""} onClick={() => { setMapLayer("illumination"); setMapStatus("Calculating illumination from the selected UTC time…"); }}>Sun illumination</button>
        </div>
        <div className="lunar-map-status" aria-live="polite">{mapStatus}</div>
        <LunarMap latitude={Number(latitude)} longitude={Number(longitude)} layer={mapLayer} observationTime={assessmentTime}
          onSelect={(lat, lon) => { setLatitude(lat.toFixed(3)); setLongitude(lon.toFixed(3)); }}
          onLoad={() => setMapStatus(mapLayer === "imagery" ? "LROC WAC imagery loaded" : mapLayer === "terrain" ? "GLD100 terrain relief loaded" : `SPICE illumination map loaded for ${new Date(assessmentTime).toISOString()}`)}
          onError={() => setMapStatus("Map tiles could not be fetched. Check your connection or try again.")} />
        <p className="map-provenance">{mapLayer === "imagery"
          ? <>Source: <a href="https://wms.lroc.asu.edu/lroc/view_rdr/WAC_GLOBAL" target="_blank" rel="noreferrer">LROC WAC global mosaic</a>, served by the Arizona State University LROC WMS. Global context imagery; not a landing safety layer.</>
          : mapLayer === "terrain"
            ? <>Source: <a href="https://wms.lroc.asu.edu/lroc/view_rdr/WAC_GLD100" target="_blank" rel="noreferrer">LROC GLD100</a> derived from WAC stereo. Shaded-relief visualization, approximately 79°S–79°N; no elevation value or slope is calculated at the selected point.</>
            : <>Source: <a href="https://webmap.lroc.asu.edu/" target="_blank" rel="noreferrer">LROC WMS GLD100 illumination layer</a>. The service uses SPICE to place the Sun for the selected UTC time. This is a visual illumination map; the API does not return pointwise visibility or duration values.</>}</p>
        <div className="selected-map-coordinates">Selected point: <strong>{Number(latitude).toFixed(3)}° lat, {Number(longitude).toFixed(3)}° lon</strong> <span>· click the map or enter coordinates below</span></div>
      </section>}
      <form className="panel assessment-form" onSubmit={analyzeSites}>
        {!compare && <label className="site-name-field">Location name<input value={siteName} maxLength="80" required onChange={(event) => setSiteName(event.target.value)} /></label>}
        {compare && <label className="site-name-field">Site A name<input value={siteName} maxLength="80" required onChange={(event) => setSiteName(event.target.value)} /></label>}
        <CoordinateFields title="Site A" latitude={latitude} longitude={longitude}
          onLatitude={setLatitude} onLongitude={setLongitude} />
        {compare && <CoordinateFields title="Site B" latitude={secondLatitude} longitude={secondLongitude}
          onLatitude={setSecondLatitude} onLongitude={setSecondLongitude} />}
        {compare && <label className="site-name-field">Site B name<input value={secondSiteName} maxLength="80" required onChange={(event) => setSecondSiteName(event.target.value)} /></label>}
        <label className="assessment-time-field">Observation time (local; sent as UTC)<input type="datetime-local" required value={assessmentTime} onChange={(event) => setAssessmentTime(event.target.value)} /></label>
        <button className="analyze-button" type="submit" disabled={loading}>
          {loading ? "CHECKING..." : compare ? "COMPARE CAPABILITIES" : explorer ? "INSPECT LOCATION" : "CHECK SITE CAPABILITIES"}
        </button>
        {error && <p className="assessment-error" role="alert">{error}</p>}
      </form>
      {assessments.map((assessment, index) => (
        <section className="panel assessment-results" key={`${assessment.site.latitude}-${assessment.site.longitude}`}>
          <div className="panel-heading">
            <div><div className="panel-kicker">{compare ? `SITE ${index + 1}` : "BACKEND RESPONSE"}</div>
              <h3>Site coordinates: {assessment.site.latitude} lat, {assessment.site.longitude} lon</h3></div>
            <span className="panel-tag">NO SCORE GENERATED</span>
          </div>
          <div className="assessment-list">
            {assessment.results.map((result) => (
              <article className="assessment-row" key={result.key}>
                <div><strong>{result.label}</strong><span>{result.reason}</span></div>
                <span className={`state-pill ${result.status.toLowerCase()}`}>{result.status}</span>
              </article>
            ))}
          </div>
          <p className="provenance-note">Requested UTC: {assessment.timestamp_utc || "not provided"} | {assessment.provenance.note} {assessment.persistence_note}</p>
        </section>
      ))}
    </div>
  );
}

function CoordinateFields({ title, latitude, longitude, onLatitude, onLongitude }) {
  return (
    <fieldset className="coordinate-fields">
      <legend>{title}</legend>
      <label>Latitude (-90 to 90)
        <input type="number" min="-90" max="90" step="any" required value={latitude}
          onChange={(event) => onLatitude(event.target.value)} />
      </label>
      <label>Longitude (-180 to 180)
        <input type="number" min="-180" max="180" step="any" required value={longitude}
          onChange={(event) => onLongitude(event.target.value)} />
      </label>
    </fieldset>
  );
}

export default App;

function LunarMap({ latitude, longitude, layer, observationTime, onSelect, onLoad, onError }) {
  const layerName = layer === "terrain" ? "luna_wac_dtm_hillshade" : layer === "illumination" ? "luna_illumination" : "luna_wac_global";
  const layerTime = layer === "illumination" ? new Date(observationTime).toISOString() : null;
  const onMapClick = (event) => onSelect(event.latlng.lat, event.latlng.lng);
  const point = [latitude, longitude];
  return <MapContainer className="lunar-leaflet-map" crs={L.CRS.EPSG4326} center={point} zoom={1}
    minZoom={0} maxZoom={7} scrollWheelZoom doubleClickZoom>
    <MapViewSync center={point} />
    <WMSTileLayer key={`${layerName}-${layerTime || "static"}`} url="https://webmap.lroc.asu.edu/"
      layers={layerName} version="1.1.1" params={layerTime ? { TIME: layerTime } : {}}
      format={layer === "illumination" ? "image/png" : "image/jpeg"} transparent={false}
      attribution={'<a href="https://www.lroc.asu.edu/">LROC / Arizona State University</a>'}
      eventHandlers={{ load: onLoad, tileerror: onError }} />
    <MapPointPicker onSelect={onMapClick} />
    <CircleMarker center={point} radius={7} pathOptions={{ color: "#f2bf63", weight: 2, fillColor: "#f2bf63", fillOpacity: 0.85 }} />
  </MapContainer>;
}

function MapViewSync({ center }) {
  const map = useMap();
  useEffect(() => { map.setView(center, map.getZoom(), { animate: false }); }, [center, map]);
  return null;
}

function MapPointPicker({ onSelect }) {
  useMapEvents({ click: onSelect });
  return null;
}
