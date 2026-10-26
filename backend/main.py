"""Gridwise AI - FastAPI Backend Service.

Provides REST API endpoints for:
- Health and readiness checks
- Model inference & status
- 24-hour forecasting and simulation
- Deterministic dispatch evaluation and critical overload alerts
- Historical persistence and CSV export
- CSV telemetry upload and schema validation
"""

import csv
import io
import os
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, File, HTTPException, Query, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, StreamingResponse
import numpy as np
import pandas as pd

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.database import (
    get_forecast_details,
    get_forecast_history,
    init_db,
)
from backend.forecast_service import run_24h_forecast
from backend.schemas import (
    Forecast24hRequest,
    Forecast24hResponse,
    HealthResponse,
    HistoryItemSchema,
    ModelStatusResponse,
    PredictBatchRequest,
    PredictBatchResponse,
)
from core.dispatch_rules import (
    CRITICAL_OVERLOAD_THRESHOLD_KW,
    DISPATCH_MODE_MAIN_GRID,
    DISPATCH_MODE_RENEWABLE_STORAGE,
    RENEWABLE_STORAGE_THRESHOLD_KW,
    evaluate_dispatch,
)
from ml.model_adapter import ModelInferenceError, adapter

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(
    title="Gridwise AI - Smart Energy Microgrid & Demand Forecasting API",
    description="End-to-end demand forecasting, dispatch decision-support, and overload alert engine.",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS configuration
allowed_origins = os.getenv("ALLOWED_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins if allowed_origins != ["*"] else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthResponse, tags=["Health"])
@app.get("/ready", response_model=HealthResponse, tags=["Health"])
def health_check():
    return HealthResponse(
        status="healthy",
        service="gridwise-ai-backend",
        timestamp=datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
        version="1.0.0",
    )


@app.get("/api/model/status", response_model=ModelStatusResponse, tags=["Model"])
def get_model_status():
    """Returns the real model status, active provider, masked endpoint, and holdout metrics."""
    return adapter.get_status()


@app.post("/api/predict", response_model=PredictBatchResponse, tags=["Inference"])
def predict_batch(request: PredictBatchRequest):
    """Executes prediction on a batch of telemetry records adhering to the inference contract."""
    if not request.data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payload contains empty 'data' array.",
        )

    records = [item.model_dump() for item in request.data]
    df = pd.DataFrame(records)

    try:
        preds = adapter.predict(df)
    except ModelInferenceError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Inference provider failure: {str(e)}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Prediction validation error: {str(e)}",
        )

    return PredictBatchResponse(
        predictions=[round(float(p), 2) for p in preds],
        count=len(preds),
        model_provider=adapter.get_status()["provider"],
        inference_timestamp=datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
    )


@app.post("/api/forecast/24h", response_model=Forecast24hResponse, tags=["Forecasting"])
def create_24h_forecast(request: Optional[Forecast24hRequest] = None):
    """Generates a complete 24-hour demand forecast, evaluates dispatch rules, and persists results."""
    input_df = None
    scenario_type = None
    start_time = None
    base_temp = None
    base_hum = None

    if request:
        if request.custom_records:
            input_df = pd.DataFrame([r.model_dump() for r in request.custom_records])
        scenario_type = request.scenario_type
        start_time = request.start_time
        base_temp = request.base_temp_c
        base_hum = request.base_humidity_pct

    try:
        result = run_24h_forecast(
            input_df=input_df,
            scenario_type=scenario_type,
            start_time=start_time,
            base_temp_c=base_temp,
            base_humidity_pct=base_hum,
            save_to_db=True,
        )
        return result
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except ModelInferenceError as me:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(me))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Forecasting engine error: {str(e)}",
        )


@app.get("/api/forecast/{forecast_id}", tags=["Forecasting"])
def get_forecast_by_id(forecast_id: str):
    """Fetches full hourly records and summary for a saved forecast run."""
    record = get_forecast_details(forecast_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Forecast ID '{forecast_id}' not found.",
        )
    return record


@app.get("/api/history", response_model=List[HistoryItemSchema], tags=["History"])
def get_history(limit: int = Query(50, ge=1, le=200)):
    """Retrieves previous forecast runs ordered by date."""
    return get_forecast_history(limit=limit)


@app.get("/api/alerts", tags=["Alerts"])
def get_active_alerts():
    """Retrieves critical overload alerts from the most recent forecast run."""
    history = get_forecast_history(limit=1)
    if not history:
        return {"active_alerts": [], "latest_run_id": None}

    latest_id = history[0]["id"]
    details = get_forecast_details(latest_id)
    if not details:
        return {"active_alerts": [], "latest_run_id": latest_id}

    overload_items = [
        item for item in details.get("data", []) if item.get("is_critical_overload")
    ]
    return {
        "latest_run_id": latest_id,
        "model_used": details.get("model_used"),
        "overload_count": len(overload_items),
        "threshold_kw": CRITICAL_OVERLOAD_THRESHOLD_KW,
        "active_alerts": overload_items,
    }


@app.get("/api/export/{forecast_id}.csv", tags=["Export"])
def export_forecast_csv(forecast_id: str):
    """Exports forecast predictions in the strict HackSphere 3.0 required CSV schema:
    timestamp,target_demand_kw
    """
    details = get_forecast_details(forecast_id)
    if not details:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Forecast ID '{forecast_id}' not found.",
        )

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["timestamp", "target_demand_kw"])

    for item in details.get("data", []):
        writer.writerow([item["timestamp"], f"{item['predicted_demand_kw']:.2f}"])

    output.seek(0)
    filename = f"gridwise_predictions_{forecast_id[:8]}.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@app.post("/api/telemetry/upload", tags=["Telemetry"])
async def upload_telemetry_csv(file: UploadFile = File(...)):
    """Validates and previews user-uploaded telemetry CSV file."""
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file must be a .csv file.",
        )

    contents = await file.read()
    if len(contents) > 10 * 1024 * 1024:  # 10 MB limit
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File size exceeds maximum limit of 10 MB.",
        )

    try:
        df = pd.read_csv(io.BytesIO(contents))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to parse CSV file: {str(e)}",
        )

    required = ["timestamp", "ambient_temp_c", "humidity_pct", "solar_irradiance_wm2"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"CSV missing required columns: {missing}. Found columns: {list(df.columns)}",
        )

    total_rows = len(df)
    null_counts = df[required].isnull().sum().to_dict()
    has_nulls = any(v > 0 for v in null_counts.values())

    preview_records = df.head(10).to_dict(orient="records")

    return {
        "filename": os.path.basename(file.filename),
        "total_rows": total_rows,
        "is_valid_schema": True,
        "can_run_24h_forecast": total_rows >= 24,
        "null_counts": null_counts,
        "has_nulls": has_nulls,
        "preview": preview_records,
    }
