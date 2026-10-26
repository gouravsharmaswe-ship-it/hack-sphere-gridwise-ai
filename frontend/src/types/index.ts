export type DispatchMode = 'Renewable Storage Mode' | 'Main Grid Mode';

export interface DispatchEvaluation {
  timestamp: string;
  local_hour: number;
  predicted_demand_kw: number;
  dispatch_mode: DispatchMode;
  is_peak_hour: boolean;
  is_demand_exceeding_160: boolean;
  is_critical_overload: boolean;
  reason: string;
}

export interface ForecastSummary {
  avg_demand_kw: number;
  peak_demand_kw: number;
  min_demand_kw: number;
  renewable_storage_hours: number;
  main_grid_hours: number;
  critical_overload_count: number;
}

export interface ForecastResponse {
  forecast_id: string;
  generated_at: string;
  model_used: string;
  is_demo_mode: boolean;
  horizon_hours: number;
  data: DispatchEvaluation[];
  summary: ForecastSummary;
}

export interface ModelStatus {
  provider: 'Zoho Catalyst QuickML' | 'Local ML Pipeline' | 'Fallback Baseline';
  endpoint_configured: boolean;
  endpoint_masked: string | null;
  status: 'active' | 'configured_unreachable' | 'unconfigured_fallback';
  last_inference_at: string | null;
  last_error: string | null;
  message: string;
  holdout_metrics?: {
    model_name: string;
    rmse: number;
    mae: number;
    split_method: string;
    train_samples: number;
    test_samples: number;
    evaluation_window: string;
  };
}

export interface HistoryItem {
  id: string;
  created_at: string;
  forecast_start: string;
  forecast_end: string;
  horizon_hours: number;
  avg_demand_kw: number;
  peak_demand_kw: number;
  overload_count: number;
  model_used: string;
  is_demo: boolean;
}

export interface TelemetryRow {
  timestamp: string;
  ambient_temp_c: number;
  humidity_pct: number;
  solar_irradiance_wm2: number;
  target_demand_kw?: number;
}
