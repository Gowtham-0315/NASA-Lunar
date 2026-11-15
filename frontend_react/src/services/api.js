const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

async function requestJson(path, options = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json", ...options.headers },
    ...options,
  });
  const data = await response.json();
  if (!response.ok) {
    const detail = typeof data.detail === "string" ? data.detail : `Backend error: ${response.status}`;
    throw new Error(detail);
  }
  return data;
}

export function getBackendHealth() {
  return requestJson("/health");
}

export function getSiteAssessment(latitude, longitude, timestampUtc) {
  const query = new URLSearchParams({ latitude, longitude, timestamp_utc: timestampUtc });
  return requestJson(`/terrain/assessment?${query}`);
}

export function createSite(site) {
  return requestJson("/sites", { method: "POST", body: JSON.stringify(site) });
}

export function getSites() {
  return requestJson("/sites");
}

export function saveAssessment(siteId, timestampUtc) {
  return requestJson(`/sites/${siteId}/assessments`, {
    method: "POST",
    body: JSON.stringify({ timestamp_utc: timestampUtc }),
  });
}

export function getSiteHistory(siteId) {
  return requestJson(`/sites/${siteId}/history`);
}