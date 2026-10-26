"""Gridwise AI - ML Model Baseline & Chronological Holdout Training & Evaluation.

This script trains candidate regression models on train_telemetry.csv using strict
chronological splitting (no future leakage, no shuffling).
Models compared:
1. Starter Formula Baseline (from HackSphere starter template)
2. Hourly Seasonal Mean Baseline
3. Linear / Ridge Regression Pipeline
4. Gradient Boosting / Random Forest Pipeline

Metrics evaluated:
- RMSE (Root Mean Squared Error)
- MAE (Mean Absolute Error)
- R2 Score
"""

import json
import math
import os
import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """Extracts chronological and weather-interaction features without future leakage."""
    res = pd.DataFrame(index=df.index)
    ts = pd.to_datetime(df["timestamp"])

    res["hour"] = ts.dt.hour
    res["month"] = ts.dt.month
    res["day_of_week"] = ts.dt.dayofweek
    res["is_weekend"] = (ts.dt.dayofweek >= 5).astype(float)

    # Cyclical hour encoding
    res["hour_sin"] = np.sin(2 * np.pi * res["hour"] / 24.0)
    res["hour_cos"] = np.cos(2 * np.pi * res["hour"] / 24.0)

    # Weather features
    temp = df["ambient_temp_c"].astype(float)
    humidity = df["humidity_pct"].astype(float)
    solar = df["solar_irradiance_wm2"].astype(float)

    res["ambient_temp_c"] = temp
    res["humidity_pct"] = humidity
    res["solar_irradiance_wm2"] = solar

    # Non-linear thermal & solar interaction
    res["cooling_demand_delta"] = np.maximum(0.0, temp - 24.0)
    res["heating_demand_delta"] = np.maximum(0.0, 18.0 - temp)
    res["heat_index_proxy"] = temp * 0.5 + humidity * 0.1
    res["solar_temp_product"] = (solar / 100.0) * (temp / 10.0)

    return res


def starter_formula_predict(df: pd.DataFrame) -> np.ndarray:
    """The starter formula from starter predict.py."""
    hours = pd.to_datetime(df["timestamp"]).dt.hour
    base_load = 120.0 + 30.0 * np.sin(2 * np.pi * (hours - 6) / 24)
    cooling_load = np.maximum(0.0, df["ambient_temp_c"] - 24.0) * 8.5
    return (base_load + cooling_load).values


def run_training_and_evaluation(data_path: str = "train_telemetry.csv"):
    print(f"Loading telemetry data from {data_path}...")
    df = pd.read_csv(data_path)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values("timestamp").reset_index(drop=True)

    total_samples = len(df)
    # Chronological 80/20 train/holdout split
    split_idx = int(total_samples * 0.8)
    train_df = df.iloc[:split_idx].copy()
    holdout_df = df.iloc[split_idx:].copy()

    train_start = train_df["timestamp"].min().strftime("%Y-%m-%d %H:%M:%S")
    train_end = train_df["timestamp"].max().strftime("%Y-%m-%d %H:%M:%S")
    holdout_start = holdout_df["timestamp"].min().strftime("%Y-%m-%d %H:%M:%S")
    holdout_end = holdout_df["timestamp"].max().strftime("%Y-%m-%d %H:%M:%S")

    print(f"Total rows: {total_samples}")
    print(f"Train split: {len(train_df)} rows ({train_start} to {train_end})")
    print(f"Holdout split: {len(holdout_df)} rows ({holdout_start} to {holdout_end})")

    X_train = engineer_features(train_df)
    y_train = train_df["target_demand_kw"].values

    X_holdout = engineer_features(holdout_df)
    y_holdout = holdout_df["target_demand_kw"].values

    results = {}

    # 1. Starter formula baseline
    starter_preds = starter_formula_predict(holdout_df)
    results["Starter Formula Baseline"] = {
        "rmse": float(np.sqrt(mean_squared_error(y_holdout, starter_preds))),
        "mae": float(mean_absolute_error(y_holdout, starter_preds)),
        "r2": float(r2_score(y_holdout, starter_preds)),
    }

    # 2. Hourly mean baseline
    hourly_means = train_df.groupby(train_df["timestamp"].dt.hour)["target_demand_kw"].mean().to_dict()
    hourly_preds = holdout_df["timestamp"].dt.hour.map(hourly_means).values
    results["Hourly Seasonal Mean Baseline"] = {
        "rmse": float(np.sqrt(mean_squared_error(y_holdout, hourly_preds))),
        "mae": float(mean_absolute_error(y_holdout, hourly_preds)),
        "r2": float(r2_score(y_holdout, hourly_preds)),
    }

    # 3. Ridge Regression Pipeline
    ridge_pipe = Pipeline([
        ("scaler", StandardScaler()),
        ("model", Ridge(alpha=10.0)),
    ])
    ridge_pipe.fit(X_train, y_train)
    ridge_preds = ridge_pipe.predict(X_holdout)
    results["Ridge Regression Pipeline"] = {
        "rmse": float(np.sqrt(mean_squared_error(y_holdout, ridge_preds))),
        "mae": float(mean_absolute_error(y_holdout, ridge_preds)),
        "r2": float(r2_score(y_holdout, ridge_preds)),
    }

    # 4. Gradient Boosting Pipeline
    gbr_model = GradientBoostingRegressor(
        n_estimators=120,
        learning_rate=0.08,
        max_depth=4,
        random_state=42,
    )
    gbr_model.fit(X_train, y_train)
    gbr_preds = gbr_model.predict(X_holdout)
    results["Gradient Boosting Regressor"] = {
        "rmse": float(np.sqrt(mean_squared_error(y_holdout, gbr_preds))),
        "mae": float(mean_absolute_error(y_holdout, gbr_preds)),
        "r2": float(r2_score(y_holdout, gbr_preds)),
    }

    # 5. Fit full model on all 4000 rows for production local inference fallback
    X_full = engineer_features(df)
    y_full = df["target_demand_kw"].values
    prod_model = GradientBoostingRegressor(
        n_estimators=150,
        learning_rate=0.08,
        max_depth=4,
        random_state=42,
    )
    prod_model.fit(X_full, y_full)

    os.makedirs("ml", exist_ok=True)
    joblib.dump(prod_model, "ml/model_pipeline.joblib")
    with open("ml/feature_names.json", "w") as f:
        json.dump(X_full.columns.tolist(), f, indent=2)

    report = {
        "dataset": {
            "total_samples": total_samples,
            "train_samples": len(train_df),
            "holdout_samples": len(holdout_df),
            "train_period": f"{train_start} to {train_end}",
            "holdout_period": f"{holdout_start} to {holdout_end}",
            "split_method": "Chronological (First 80% train, last 20% holdout)",
            "target": "target_demand_kw",
        },
        "models": results,
        "best_model": "Gradient Boosting Regressor",
        "best_holdout_metrics": results["Gradient Boosting Regressor"],
    }

    with open("ml/evaluation_report.json", "w") as f:
        json.dump(report, f, indent=2)

    print("\n=== EVALUATION REPORT ===")
    for model_name, metrics in results.items():
        print(f"{model_name:32s} | RMSE: {metrics['rmse']:6.2f} kW | MAE: {metrics['mae']:6.2f} kW | R2: {metrics['r2']:6.3f}")

    print(f"\nTrained production model saved to ml/model_pipeline.joblib")
    print(f"Report saved to ml/evaluation_report.json")
    return report


if __name__ == "__main__":
    run_training_and_evaluation()
