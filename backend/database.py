"""SQLite database persistence for Gridwise AI forecast history and telemetry."""

import os
import sqlite3
from datetime import datetime
from typing import Any, Dict, List, Optional
import json

DB_FILE = os.getenv("GRIDWISE_DB_PATH", "gridwise_history.db")


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Initialize database tables for forecast history and telemetry."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS forecast_history (
                id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                forecast_start TEXT NOT NULL,
                forecast_end TEXT NOT NULL,
                horizon_hours INTEGER NOT NULL,
                avg_demand_kw REAL NOT NULL,
                peak_demand_kw REAL NOT NULL,
                overload_count INTEGER NOT NULL,
                model_used TEXT NOT NULL,
                is_demo INTEGER NOT NULL,
                summary_json TEXT NOT NULL
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS forecast_hourly_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                forecast_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                local_hour INTEGER NOT NULL,
                predicted_demand_kw REAL NOT NULL,
                dispatch_mode TEXT NOT NULL,
                is_peak_hour INTEGER NOT NULL,
                is_demand_exceeding_160 INTEGER NOT NULL,
                is_critical_overload INTEGER NOT NULL,
                reason TEXT NOT NULL,
                FOREIGN KEY (forecast_id) REFERENCES forecast_history(id) ON DELETE CASCADE
            )
            """
        )
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_forecast_id ON forecast_hourly_records(forecast_id);
            """
        )
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_timestamp ON forecast_hourly_records(timestamp);
            """
        )
        conn.commit()


def save_forecast_run(
    forecast_id: str,
    created_at: str,
    forecast_start: str,
    forecast_end: str,
    horizon_hours: int,
    avg_demand_kw: float,
    peak_demand_kw: float,
    overload_count: int,
    model_used: str,
    is_demo: bool,
    summary: Dict[str, Any],
    hourly_records: List[Dict[str, Any]],
) -> None:
    """Saves a complete forecast run and all associated hourly records atomically."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT OR REPLACE INTO forecast_history 
            (id, created_at, forecast_start, forecast_end, horizon_hours, avg_demand_kw, peak_demand_kw, overload_count, model_used, is_demo, summary_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                forecast_id,
                created_at,
                forecast_start,
                forecast_end,
                horizon_hours,
                round(avg_demand_kw, 2),
                round(peak_demand_kw, 2),
                overload_count,
                model_used,
                1 if is_demo else 0,
                json.dumps(summary),
            ),
        )

        for rec in hourly_records:
            cursor.execute(
                """
                INSERT INTO forecast_hourly_records 
                (forecast_id, timestamp, local_hour, predicted_demand_kw, dispatch_mode, is_peak_hour, is_demand_exceeding_160, is_critical_overload, reason)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    forecast_id,
                    rec["timestamp"],
                    rec["local_hour"],
                    round(rec["predicted_demand_kw"], 2),
                    rec["dispatch_mode"],
                    1 if rec["is_peak_hour"] else 0,
                    1 if rec["is_demand_exceeding_160"] else 0,
                    1 if rec["is_critical_overload"] else 0,
                    rec["reason"],
                ),
            )
        conn.commit()


def get_forecast_history(limit: int = 50) -> List[Dict[str, Any]]:
    """Retrieves previous forecast runs ordered by creation timestamp."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, created_at, forecast_start, forecast_end, horizon_hours, avg_demand_kw, peak_demand_kw, overload_count, model_used, is_demo
            FROM forecast_history
            ORDER BY datetime(created_at) DESC
            LIMIT ?
            """,
            (limit,),
        )
        rows = cursor.fetchall()
        return [
            {
                "id": r["id"],
                "created_at": r["created_at"],
                "forecast_start": r["forecast_start"],
                "forecast_end": r["forecast_end"],
                "horizon_hours": r["horizon_hours"],
                "avg_demand_kw": r["avg_demand_kw"],
                "peak_demand_kw": r["peak_demand_kw"],
                "overload_count": r["overload_count"],
                "model_used": r["model_used"],
                "is_demo": bool(r["is_demo"]),
            }
            for r in rows
        ]


def get_forecast_details(forecast_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves detailed hourly records for a specific forecast run."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, created_at, forecast_start, forecast_end, horizon_hours, avg_demand_kw, peak_demand_kw, overload_count, model_used, is_demo, summary_json
            FROM forecast_history
            WHERE id = ?
            """,
            (forecast_id,),
        )
        run_row = cursor.fetchone()
        if not run_row:
            return None

        cursor.execute(
            """
            SELECT timestamp, local_hour, predicted_demand_kw, dispatch_mode, is_peak_hour, is_demand_exceeding_160, is_critical_overload, reason
            FROM forecast_hourly_records
            WHERE forecast_id = ?
            ORDER BY timestamp ASC
            """,
            (forecast_id,),
        )
        item_rows = cursor.fetchall()
        return {
            "id": run_row["id"],
            "created_at": run_row["created_at"],
            "forecast_start": run_row["forecast_start"],
            "forecast_end": run_row["forecast_end"],
            "horizon_hours": run_row["horizon_hours"],
            "model_used": run_row["model_used"],
            "is_demo": bool(run_row["is_demo"]),
            "summary": json.loads(run_row["summary_json"]),
            "data": [
                {
                    "timestamp": r["timestamp"],
                    "local_hour": r["local_hour"],
                    "predicted_demand_kw": r["predicted_demand_kw"],
                    "dispatch_mode": r["dispatch_mode"],
                    "is_peak_hour": bool(r["is_peak_hour"]),
                    "is_demand_exceeding_160": bool(r["is_demand_exceeding_160"]),
                    "is_critical_overload": bool(r["is_critical_overload"]),
                    "reason": r["reason"],
                }
                for r in item_rows
            ],
        }
