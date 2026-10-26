"""Pydantic schemas for Gridwise AI FastAPI backend."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class TelemetryItem(BaseModel):
    timestamp: str = Field(..., description="Hourly timestamp, e.g. '2024-01-01 00:00:00'")
    ambient_temp_c: float = Field(..., description="Ambient temperature in degrees Celsius")
    humidity_pct: float = Field(..., description="Relative humidity percentage (0-100)")
    solar_irradiance_wm2: float = Field(..., description="Solar irradiance in W/m2")


class PredictBatchRequest(BaseModel):
    data: List[TelemetryItem] = Field(..., description="List of telemetry records to forecast")


class PredictBatchResponse(BaseModel):
    predictions: List[float]
    count: int
    model_provider: str
    inference_timestamp: str


class Forecast24hRequest(BaseModel):
    scenario_type: Optional[str] = Field(
        None,
        description="Optional scenario mode ('summer_peak', 'moderate_spring', 'heatwave_overload')",
    )
    start_time: Optional[str] = Field(
        None,
        description="Forecast horizon start timestamp (YYYY-MM-DD HH:00:00)",
    )
    base_temp_c: Optional[float] = Field(None, description="Custom base temperature in Celsius")
    base_humidity_pct: Optional[float] = Field(None, description="Custom base humidity percentage")
    custom_records: Optional[List[TelemetryItem]] = Field(
        None,
        description="24 custom hourly telemetry records if provided directly",
    )


class WeatherData(BaseModel):
    ambient_temp_c: float
    humidity_pct: float
    solar_irradiance_wm2: float


class HourlyForecastItem(BaseModel):
    timestamp: str
    local_hour: int
    predicted_demand_kw: float
    dispatch_mode: str
    is_peak_hour: bool
    is_demand_exceeding_160: bool
    is_critical_overload: bool
    reason: str
    weather: Optional[WeatherData] = None


class ForecastSummarySchema(BaseModel):
    avg_demand_kw: float
    peak_demand_kw: float
    min_demand_kw: float
    renewable_storage_hours: int
    main_grid_hours: int
    critical_overload_count: int


class Forecast24hResponse(BaseModel):
    forecast_id: str
    generated_at: str
    model_used: str
    is_demo_mode: bool
    horizon_hours: int
    data: List[HourlyForecastItem]
    summary: ForecastSummarySchema


class HoldoutMetricsSchema(BaseModel):
    model_name: str
    rmse: float
    mae: float
    split_method: str
    train_samples: int
    test_samples: int
    evaluation_window: str


class ModelStatusResponse(BaseModel):
    provider: str
    endpoint_configured: bool
    endpoint_masked: Optional[str] = None
    status: str
    last_inference_at: Optional[str] = None
    last_error: Optional[str] = None
    message: str
    holdout_metrics: Optional[HoldoutMetricsSchema] = None


class HistoryItemSchema(BaseModel):
    id: str
    created_at: str
    forecast_start: str
    forecast_end: str
    horizon_hours: int
    avg_demand_kw: float
    peak_demand_kw: float
    overload_count: int
    model_used: str
    is_demo: bool


class HealthResponse(BaseModel):
    status: str
    service: str
    timestamp: str
    version: str
