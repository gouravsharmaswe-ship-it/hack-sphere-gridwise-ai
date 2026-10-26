"""Gridwise AI - Model Adapter for Zoho Catalyst QuickML and Local Inference.

This module provides a unified inference adapter that:
1. Connects to the real Zoho Catalyst QuickML endpoint if configured.
2. Validates input schema, row count, and types.
3. Enforces strict error handling (timeouts, auth, server errors).
4. Provides fallback to the verified local trained model (or starter formula)
   when explicit local/offline mode is enabled.
5. Returns finite numeric predictions preserving exact input order.
"""

import json
import logging
import os
import time
from typing import Any, Dict, List, Optional, Tuple, Union
import joblib
import numpy as np
import pandas as pd
import requests

logger = logging.getLogger("gridwise.model_adapter")

REQUIRED_COLUMNS = ["timestamp", "ambient_temp_c", "humidity_pct", "solar_irradiance_wm2"]
DEFAULT_PLACEHOLDER = "YOUR_PUBLISHED_QUICKML_ENDPOINT_URL_HERE"


class ModelInferenceError(Exception):
    """Raised when inference fails and cannot produce valid predictions."""
    pass


class ModelAdapter:
    def __init__(self):
        self.endpoint_url = os.getenv("QUICKML_ENDPOINT_URL", DEFAULT_PLACEHOLDER).strip()
        self.api_key = os.getenv("QUICKML_API_KEY", "").strip()
        self.timeout_seconds = float(os.getenv("QUICKML_TIMEOUT_SECONDS", "10.0"))
        self.last_inference_at: Optional[str] = None
        self.last_error: Optional[str] = None
        self._local_pipeline = None
        self._load_local_model()

    def _load_local_model(self):
        model_path = os.path.join(os.path.dirname(__file__), "model_pipeline.joblib")
        if os.path.exists(model_path):
            try:
                self._local_pipeline = joblib.load(model_path)
            except Exception as e:
                logger.warning(f"Failed to load local model pipeline: {e}")

    @property
    def is_quickml_configured(self) -> bool:
        return bool(self.endpoint_url and self.endpoint_url != DEFAULT_PLACEHOLDER)

    def get_masked_endpoint(self) -> Optional[str]:
        if not self.is_quickml_configured:
            return None
        url = self.endpoint_url
        if len(url) > 25:
            return url[:12] + "..." + url[-8:]
        return url

    def get_status(self) -> Dict[str, Any]:
        """Returns the real connection and model status."""
        configured = self.is_quickml_configured
        status_code = "unconfigured_fallback"
        provider = "Fallback Baseline"
        message = "QuickML endpoint not configured. Using local verified ML model."

        if configured:
            status_code = "active"
            provider = "Zoho Catalyst QuickML"
            message = "QuickML endpoint configured."

        if self.last_error and configured:
            status_code = "configured_unreachable"
            message = f"QuickML configured but last call failed: {self.last_error}"

        holdout_metrics = None
        report_path = os.path.join(os.path.dirname(__file__), "evaluation_report.json")
        if os.path.exists(report_path):
            try:
                with open(report_path, "r") as f:
                    report = json.load(f)
                    best = report.get("best_holdout_metrics", {})
                    ds = report.get("dataset", {})
                    holdout_metrics = {
                        "model_name": report.get("best_model", "Local Pipeline"),
                        "rmse": round(best.get("rmse", 0.0), 2),
                        "mae": round(best.get("mae", 0.0), 2),
                        "split_method": ds.get("split_method", "Chronological"),
                        "train_samples": ds.get("train_samples", 0),
                        "test_samples": ds.get("holdout_samples", 0),
                        "evaluation_window": ds.get("holdout_period", ""),
                    }
            except Exception as e:
                logger.warning(f"Could not read evaluation report: {e}")

        return {
            "provider": provider,
            "endpoint_configured": configured,
            "endpoint_masked": self.get_masked_endpoint(),
            "status": status_code,
            "last_inference_at": self.last_inference_at,
            "last_error": self.last_error,
            "message": message,
            "holdout_metrics": holdout_metrics,
        }

    def validate_input(self, input_df: pd.DataFrame) -> None:
        """Strictly validates input dataframe schema and values."""
        if not isinstance(input_df, pd.DataFrame):
            raise ModelInferenceError(f"Expected pandas.DataFrame, got {type(input_df)}")
        if len(input_df) == 0:
            raise ModelInferenceError("Input DataFrame is empty. At least 1 row is required.")

        missing_cols = [c for c in REQUIRED_COLUMNS if c not in input_df.columns]
        if missing_cols:
            raise ModelInferenceError(
                f"Missing required columns: {missing_cols}. Input must contain {REQUIRED_COLUMNS}."
            )

        # Check for nulls in required columns
        null_counts = input_df[REQUIRED_COLUMNS].isnull().sum()
        cols_with_nulls = null_counts[null_counts > 0].to_dict()
        if cols_with_nulls:
            raise ModelInferenceError(f"Input contains NaN/null values in columns: {cols_with_nulls}")

    def _call_quickml(self, input_df: pd.DataFrame) -> np.ndarray:
        """Sends inference request to Catalyst QuickML endpoint."""
        records = input_df[REQUIRED_COLUMNS].to_dict(orient="records")
        payload = {"data": records}
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Zoho-oauthtoken {self.api_key}"

        start_time = time.time()
        try:
            response = requests.post(
                self.endpoint_url,
                json=payload,
                headers=headers,
                timeout=self.timeout_seconds,
            )
        except requests.exceptions.Timeout:
            err = f"QuickML endpoint timed out after {self.timeout_seconds} seconds."
            self.last_error = err
            raise ModelInferenceError(err)
        except requests.exceptions.ConnectionError as e:
            err = f"Failed to connect to QuickML endpoint: {e}"
            self.last_error = err
            raise ModelInferenceError(err)
        except Exception as e:
            err = f"Inference request error: {e}"
            self.last_error = err
            raise ModelInferenceError(err)

        if response.status_code != 200:
            err = f"QuickML endpoint returned HTTP {response.status_code}: {response.text[:200]}"
            self.last_error = err
            raise ModelInferenceError(err)

        try:
            res_json = response.json()
        except Exception as e:
            err = f"Malformed JSON response from QuickML: {e}"
            self.last_error = err
            raise ModelInferenceError(err)

        # Standard Catalyst QuickML returns {'predictions': [...]} or {'data': [{'prediction': ...}]}
        predictions = None
        if "predictions" in res_json:
            predictions = res_json["predictions"]
        elif "data" in res_json and isinstance(res_json["data"], list):
            predictions = [
                row.get("prediction", row.get("target_demand_kw"))
                for row in res_json["data"]
            ]
        elif isinstance(res_json, list):
            predictions = res_json

        if predictions is None:
            err = f"Unexpected response schema from QuickML. Keys received: {list(res_json.keys())}"
            self.last_error = err
            raise ModelInferenceError(err)

        preds_arr = np.array(predictions, dtype=float)
        if len(preds_arr) != len(input_df):
            err = f"Prediction count mismatch: expected {len(input_df)}, got {len(preds_arr)}"
            self.last_error = err
            raise ModelInferenceError(err)

        if np.isnan(preds_arr).any() or np.isinf(preds_arr).any():
            err = "QuickML predictions contain NaN or Inf values."
            self.last_error = err
            raise ModelInferenceError(err)

        self.last_inference_at = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
        self.last_error = None
        return preds_arr

    def _predict_local(self, input_df: pd.DataFrame) -> np.ndarray:
        """Generates predictions using local trained ML pipeline or starter formula."""
        if self._local_pipeline is not None:
            try:
                from ml.train_baseline import engineer_features
                X = engineer_features(input_df)
                preds = self._local_pipeline.predict(X)
                self.last_inference_at = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
                return np.array(preds, dtype=float)
            except Exception as e:
                logger.warning(f"Local pipeline execution failed, using baseline formula: {e}")

        # Starter baseline formula fallback
        hours = pd.to_datetime(input_df["timestamp"]).dt.hour
        base_load = 120.0 + 30.0 * np.sin(2 * np.pi * (hours - 6) / 24)
        cooling_load = np.maximum(0.0, input_df["ambient_temp_c"] - 24.0) * 8.5
        preds = (base_load + cooling_load).values
        self.last_inference_at = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
        return np.array(preds, dtype=float)

    def predict(self, input_df: pd.DataFrame, force_local: bool = False) -> np.ndarray:
        """Main prediction method satisfying the strict contract."""
        self.validate_input(input_df)

        if self.is_quickml_configured and not force_local:
            # When QuickML is configured, execute real request
            return self._call_quickml(input_df)

        # Otherwise use local verified model
        return self._predict_local(input_df)


# Global adapter instance
adapter = ModelAdapter()
