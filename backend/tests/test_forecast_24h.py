"""Tests for 24-hour forecasting workflow, timestamp validation and scenarios."""

from datetime import datetime, timedelta
import os
import sys
import unittest
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from backend.forecast_service import (
    generate_diurnal_weather_scenario,
    run_24h_forecast,
    validate_24h_dataframe,
)


class TestForecast24h(unittest.TestCase):

    def setUp(self):
        start = datetime(2024, 6, 1, 0, 0, 0)
        self.valid_24h_df = pd.DataFrame({
            "timestamp": [(start + timedelta(hours=i)).strftime("%Y-%m-%d %H:%M:%S") for i in range(24)],
            "ambient_temp_c": [22.0 + i * 0.5 for i in range(24)],
            "humidity_pct": [60.0 for _ in range(24)],
            "solar_irradiance_wm2": [100.0 if 6 <= i <= 18 else 0.0 for i in range(24)],
        })

    def test_valid_24h_dataframe_passes(self):
        validated = validate_24h_dataframe(self.valid_24h_df)
        self.assertEqual(len(validated), 24)

    def test_fewer_than_24_rows_fails(self):
        short_df = self.valid_24h_df.iloc[:20].copy()
        with self.assertRaises(ValueError) as ctx:
            validate_24h_dataframe(short_df)
        self.assertIn("at least 24 rows", str(ctx.exception))

    def test_non_consecutive_hourly_timestamps_fail(self):
        gap_df = self.valid_24h_df.copy()
        # Introduce a 2-hour gap at index 10
        gap_df.loc[10, "timestamp"] = "2024-06-01 12:00:00"  # instead of 10:00:00
        with self.assertRaises(ValueError) as ctx:
            validate_24h_dataframe(gap_df)
        self.assertIn("consecutive hourly", str(ctx.exception))

    def test_run_24h_forecast_returns_valid_structure(self):
        res = run_24h_forecast(input_df=self.valid_24h_df, save_to_db=False)
        self.assertIn("forecast_id", res)
        self.assertIn("data", res)
        self.assertIn("summary", res)
        self.assertEqual(len(res["data"]), 24)

        # Check hourly item keys
        first_item = res["data"][0]
        self.assertIn("timestamp", first_item)
        self.assertIn("predicted_demand_kw", first_item)
        self.assertIn("dispatch_mode", first_item)
        self.assertIn("is_critical_overload", first_item)

    def test_diurnal_weather_scenario_generates_24_consecutive_hours(self):
        scenario_df = generate_diurnal_weather_scenario("2024-07-01 00:00:00", scenario_type="summer_peak")
        self.assertEqual(len(scenario_df), 24)
        validated = validate_24h_dataframe(scenario_df)
        self.assertEqual(len(validated), 24)


if __name__ == "__main__":
    unittest.main()
