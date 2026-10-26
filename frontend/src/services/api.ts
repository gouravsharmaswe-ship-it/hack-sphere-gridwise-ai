import { ForecastResponse, HistoryItem, ModelStatus } from '../types';

const API_BASE = '/api';

export async function fetchHealth() {
  const res = await fetch('/health');
  if (!res.ok) throw new Error('Health check failed');
  return res.json();
}

export async function fetchModelStatus(): Promise<ModelStatus> {
  const res = await fetch(`${API_BASE}/model/status`);
  if (!res.ok) throw new Error('Failed to fetch model status');
  return res.json();
}

export async function fetchHistory(limit = 20): Promise<HistoryItem[]> {
  const res = await fetch(`${API_BASE}/history?limit=${limit}`);
  if (!res.ok) throw new Error('Failed to fetch forecast history');
  return res.json();
}

export async function request24hForecast(payload: {
  scenario_type?: string;
  start_time?: string;
  base_temp_c?: number;
  base_humidity_pct?: number;
}): Promise<ForecastResponse> {
  const res = await fetch(`${API_BASE}/forecast/24h`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || 'Forecasting request failed');
  }
  return res.json();
}

export async function fetchForecastById(forecastId: string): Promise<ForecastResponse> {
  const res = await fetch(`${API_BASE}/forecast/${forecastId}`);
  if (!res.ok) throw new Error(`Failed to load forecast ${forecastId}`);
  return res.json();
}

export async function uploadTelemetryCsv(file: File) {
  const formData = new FormData();
  formData.append('file', file);

  const res = await fetch(`${API_BASE}/telemetry/upload`, {
    method: 'POST',
    body: formData,
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || 'Telemetry upload failed');
  }
  return res.json();
}

export function getExportCsvUrl(forecastId: string): string {
  return `${API_BASE}/export/${forecastId}.csv`;
}
