"""Integration tests for FastAPI endpoints."""

import os
import sys
import unittest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from backend.main import app
from backend.database import init_db


class TestApiEndpoints(unittest.TestCase):

    def setUp(self):
        init_db()
        self.client = TestClient(app)

    def test_health_check(self):
        res = self.client.get("/health")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "healthy")
        self.assertEqual(data["service"], "gridwise-ai-backend")

    def test_model_status_endpoint(self):
        res = self.client.get("/api/model/status")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("provider", data)
        self.assertIn("status", data)
        self.assertIn("holdout_metrics", data)

    def test_predict_batch_endpoint(self):
        payload = {
            "data": [
                {
                    "timestamp": "2024-01-01 00:00:00",
                    "ambient_temp_c": 15.0,
                    "humidity_pct": 60.0,
                    "solar_irradiance_wm2": 0.0,
                },
                {
                    "timestamp": "2024-01-01 01:00:00",
                    "ambient_temp_c": 14.5,
                    "humidity_pct": 62.0,
                    "solar_irradiance_wm2": 0.0,
                },
            ]
        }
        res = self.client.post("/api/predict", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["count"], 2)
        self.assertEqual(len(data["predictions"]), 2)

    def test_forecast_24h_scenario_endpoint(self):
        payload = {
            "scenario_type": "summer_peak",
            "start_time": "2024-07-01 00:00:00",
        }
        res = self.client.post("/api/forecast/24h", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["horizon_hours"], 24)
        self.assertEqual(len(data["data"]), 24)
        self.assertIn("summary", data)
        self.assertIn("avg_demand_kw", data["summary"])

    def test_history_endpoint(self):
        res = self.client.get("/api/history?limit=10")
        self.assertEqual(res.status_code, 200)
        self.assertIsInstance(res.json(), list)

    def test_csv_upload_validation(self):
        # Valid CSV
        valid_csv = "timestamp,ambient_temp_c,humidity_pct,solar_irradiance_wm2\n2024-01-01 00:00:00,10.0,50.0,0.0\n"
        res = self.client.post(
            "/api/telemetry/upload",
            files={"file": ("test.csv", valid_csv.encode("utf-8"), "text/csv")},
        )
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.json()["is_valid_schema"])

        # Invalid CSV missing required columns
        invalid_csv = "timestamp,ambient_temp_c\n2024-01-01 00:00:00,10.0\n"
        res_inv = self.client.post(
            "/api/telemetry/upload",
            files={"file": ("bad.csv", invalid_csv.encode("utf-8"), "text/csv")},
        )
        self.assertEqual(res_inv.status_code, 422)


if __name__ == "__main__":
    unittest.main()
