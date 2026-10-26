"""Gridwise AI - 24-Hour Forecasting Workflow Service.

Provides:
- Strict validation of 24 consecutive hourly timestamps.
- Handling of real uploaded telemetry vs honestly labelled user-configurable scenarios.
- Prediction using the ModelAdapter.
- Application of deterministic dispatch rules and independent overload alerts.
- Persisting forecast run and hourly details to SQLite.
"""

from datetime import datetime, timedelta
import os
import uuid
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import pandas as pd

from core.dispatch_rules import evaluate_dispatch
from ml.model_adapter import adapter, ModelInferenceError
from backend.database import save_forecast_run


def validate_24h_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Validates that input DataFrame has at least 24 consecutive hourly rows with required features."""
    required = ["timestamp", "ambient_temp_c", "humidity_pct", "solar_irradiance_wm2"]
    for col in required:
        if col not in df.columns:
            raise ValueError(f"Missing required feature column: '{col}'")

    if len(df) < 24:
        raise ValueError(f"Forecast horizon requires at least 24 rows, but only {len(df)} rows were provided.")

    df_24 = df.iloc[:24].copy()
    timestamps = pd.to_datetime(df_24["timestamp"])

    # Check for consecutive 1-hour steps
    for i in range(len(timestamps) - 1):
        diff_seconds = (timestamps.iloc[i + 1] - timestamps.iloc[i]).total_seconds()
        if abs(diff_seconds - 3600.0) > 1.0:
            raise ValueError(
                f"Timestamps must be consecutive hourly steps. Gap found between row {i} ({timestamps.iloc[i]}) and row {i+1} ({timestamps.iloc[i+1]})."
            )

    # Check for NaNs
    if df_24[required].isnull().any().any():
        raise ValueError("Provided telemetry contains NaN or null values in required columns.")

    return df_24


def generate_diurnal_weather_scenario(
    start_time: str,
    scenario_type: str = "summer_peak",
    base_temp_c: Optional[float] = None,
    base_humidity_pct: Optional[float] = None,
) -> pd.DataFrame:
    """Generates an honestly labelled 24-hour weather scenario for simulation/testing."""
    dt_start = datetime.strptime(start_time.strip()[:19].replace("T", " "), "%Y-%m-%d %H:%M:%S")

    timestamps = [dt_start + timedelta(hours=i) for i in range(24)]
    hours = [t.hour for t in timestamps]

    rows = []
    for t, h in zip(timestamps, hours):
        if scenario_type == "summer_peak":
            # Peak heat in afternoon 14:00-16:00, warm night
            t_base = base_temp_c if base_temp_c is not None else 32.0
            temp = t_base + 6.0 * np.sin(np.pi * (h - 9) / 12) if 6 <= h <= 21 else t_base - 3.0
            hum = (base_humidity_pct if base_humidity_pct is not None else 55.0) - 10.0 * np.sin(np.pi * (h - 9) / 12)
            solar = max(0.0, 420.0 * np.sin(np.pi * (h - 6) / 12)) if 6 <= h <= 18 else 0.0

        elif scenario_type == "moderate_spring":
            t_base = base_temp_c if base_temp_c is not None else 20.0
            temp = t_base + 4.5 * np.sin(np.pi * (h - 9) / 12) if 6 <= h <= 21 else t_base - 2.5
            hum = (base_humidity_pct if base_humidity_pct is not None else 65.0)
            solar = max(0.0, 280.0 * np.sin(np.pi * (h - 6) / 12)) if 6 <= h <= 18 else 0.0

        elif scenario_type == "heatwave_overload":
            # Stress-testing scenario designed to trigger overload >= 200 kW
            t_base = base_temp_c if base_temp_c is not None else 37.0
            temp = t_base + 7.5 * np.sin(np.pi * (h - 9) / 12) if 6 <= h <= 21 else t_base - 1.5
            hum = (base_humidity_pct if base_humidity_pct is not None else 60.0)
            solar = max(0.0, 480.0 * np.sin(np.pi * (h - 6) / 12)) if 6 <= h <= 18 else 0.0

        else:
            t_base = base_temp_c if base_temp_c is not None else 22.0
            temp = t_base
            hum = base_humidity_pct if base_humidity_pct is not None else 60.0
            solar = 50.0 if 7 <= h <= 17 else 0.0

        rows.append({
            "timestamp": t.strftime("%Y-%m-%d %H:%M:%S"),
            "ambient_temp_c": round(float(temp), 2),
            "humidity_pct": round(float(np.clip(hum, 20.0, 95.0)), 2),
            "solar_irradiance_wm2": round(float(max(0.0, solar)), 2),
        })

    return pd.DataFrame(rows)


def run_24h_forecast(
    input_df: Optional[pd.DataFrame] = None,
    scenario_type: Optional[str] = None,
    start_time: Optional[str] = None,
    base_temp_c: Optional[float] = None,
    base_humidity_pct: Optional[float] = None,
    save_to_db: bool = True,
) -> Dict[str, Any]:
    """Generates a 24-hour forecast and evaluates deterministic dispatch rules."""
    is_demo = False
    model_name = adapter.get_status()["provider"]

    if input_df is not None:
        df_24 = validate_24h_dataframe(input_df)
    elif scenario_type:
        is_demo = True
        st = start_time or datetime.now().strftime("%Y-%m-%d %H:00:00")
        df_24 = generate_diurnal_weather_scenario(
            st,
            scenario_type=scenario_type,
            base_temp_c=base_temp_c,
            base_humidity_pct=base_humidity_pct,
        )
    else:
        # Default fallback: load first 24 hours from sample_test_input.csv
        test_path = "sample_test_input.csv"
        if os.path.exists(test_path):
            sample_df = pd.read_csv(test_path)
            df_24 = sample_df.iloc[:24].copy()
        else:
            is_demo = True
            st = datetime.now().strftime("%Y-%m-%d %H:00:00")
            df_24 = generate_diurnal_weather_scenario(st, scenario_type="summer_peak")

    # Generate predictions via ModelAdapter
    predictions = adapter.predict(df_24)

    # Evaluate deterministic dispatch rules for each row
    hourly_evaluations: List[Dict[str, Any]] = []
    overload_count = 0
    renewable_storage_count = 0
    main_grid_count = 0

    for i in range(len(df_24)):
        row = df_24.iloc[i]
        ts_str = str(row["timestamp"])
        pred_kw = float(predictions[i])

        eval_result = evaluate_dispatch(pred_kw, ts_str)

        if eval_result.is_critical_overload:
            overload_count += 1
        if eval_result.dispatch_mode == "Renewable Storage Mode":
            renewable_storage_count += 1
        else:
            main_grid_count += 1

        hourly_evaluations.append({
            "timestamp": ts_str,
            "local_hour": eval_result.local_hour,
            "predicted_demand_kw": round(pred_kw, 2),
            "dispatch_mode": eval_result.dispatch_mode,
            "is_peak_hour": eval_result.is_peak_hour,
            "is_demand_exceeding_160": eval_result.is_demand_exceeding_160,
            "is_critical_overload": eval_result.is_critical_overload,
            "reason": eval_result.reason,
            "weather": {
                "ambient_temp_c": float(row["ambient_temp_c"]),
                "humidity_pct": float(row["humidity_pct"]),
                "solar_irradiance_wm2": float(row["solar_irradiance_wm2"]),
            },
        })

    demands = [h["predicted_demand_kw"] for h in hourly_evaluations]
    summary = {
        "avg_demand_kw": round(float(np.mean(demands)), 2),
        "peak_demand_kw": round(float(np.max(demands)), 2),
        "min_demand_kw": round(float(np.min(demands)), 2),
        "renewable_storage_hours": renewable_storage_count,
        "main_grid_hours": main_grid_count,
        "critical_overload_count": overload_count,
    }

    forecast_id = str(uuid.uuid4())
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    start_ts = hourly_evaluations[0]["timestamp"]
    end_ts = hourly_evaluations[-1]["timestamp"]

    if save_to_db:
        save_forecast_run(
            forecast_id=forecast_id,
            created_at=created_at,
            forecast_start=start_ts,
            forecast_end=end_ts,
            horizon_hours=24,
            avg_demand_kw=summary["avg_demand_kw"],
            peak_demand_kw=summary["peak_demand_kw"],
            overload_count=summary["critical_overload_count"],
            model_used=model_name,
            is_demo=is_demo,
            summary=summary,
            hourly_records=hourly_evaluations,
        )

    return {
        "forecast_id": forecast_id,
        "generated_at": created_at,
        "model_used": model_name,
        "is_demo_mode": is_demo,
        "horizon_hours": 24,
        "data": hourly_evaluations,
        "summary": summary,
    }
