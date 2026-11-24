/**
 * MeterGuard AI - Centralized API Service
 */

const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL || "http://localhost:5000"
).replace(/\/+$/, "");

export async function fetchDashboard() {
  const response = await fetch(`${API_BASE_URL}/api/dashboard`);
  if (!response.ok) {
    throw new Error(`Backend returned HTTP ${response.status}`);
  }
  return await response.json();
}

export async function fetchHealth() {
  const response = await fetch(`${API_BASE_URL}/api/health`);
  if (!response.ok) {
    throw new Error(`Backend returned HTTP ${response.status}`);
  }
  return await response.json();
}

export async function fetchMeters() {
  const response = await fetch(`${API_BASE_URL}/api/meters`);
  if (!response.ok) {
    throw new Error(`Backend returned HTTP ${response.status}`);
  }
  return await response.json();
}

export async function fetchMeterById(meterId) {
  const response = await fetch(`${API_BASE_URL}/api/meter/${meterId}`);
  if (!response.ok) {
    throw new Error(`Backend returned HTTP ${response.status}`);
  }
  return await response.json();
}

export async function analyzeAnomalySequence(meterId, sequenceType, consumption) {
  const response = await fetch(`${API_BASE_URL}/api/anomaly/analyze`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      meter_id: meterId,
      sequence_type: sequenceType,
      consumption: consumption,
    }),
  });
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.message || `Backend returned HTTP ${response.status}`);
  }
  return await response.json();
}

export async function simulateTampering(meterId, scenario, autoGenerateReport = true) {
  const response = await fetch(`${API_BASE_URL}/api/simulate/tamper`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      meter_id: meterId,
      scenario: scenario,
      auto_generate_report: autoGenerateReport,
    }),
  });
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.message || `Simulation failed with HTTP ${response.status}`);
  }
  return await response.json();
}

export async function generateInvestigationReport(meterId, alertId = null) {
  const response = await fetch(`${API_BASE_URL}/api/reports/generate`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      meter_id: meterId,
      alert_id: alertId,
    }),
  });
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.message || `Report generation failed with HTTP ${response.status}`);
  }
  return await response.json();
}

export async function fetchMeterReports(meterId) {
  const response = await fetch(`${API_BASE_URL}/api/reports/${encodeURIComponent(meterId)}`);
  if (!response.ok) {
    throw new Error(`Failed to fetch reports for ${meterId} (HTTP ${response.status})`);
  }
  return await response.json();
}

export async function fetchAlerts(meterId = null) {
  const url = meterId
    ? `${API_BASE_URL}/api/alerts?meter_id=${encodeURIComponent(meterId)}`
    : `${API_BASE_URL}/api/alerts`;
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Failed to fetch alerts (HTTP ${response.status})`);
  }
  return await response.json();
}

export { API_BASE_URL };
