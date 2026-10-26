"""Contract tests for predict() function and model adapter."""

import os
import sys
import unittest
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from predict import predict
from ml.model_adapter import adapter, ModelInferenceError


class TestPredictContract(unittest.TestCase):

    def setUp(self):
        # 5 sample rows
        self.sample_df = pd.DataFrame({
            "timestamp": [
                "2024-01-01 00:00:00",
                "2024-01-01 01:00:00",
                "2024-01-01 02:00:00",
                "2024-01-01 03:00:00",
                "2024-01-01 04:00:00",
            ],
            "ambient_temp_c": [12.5, 11.8, 11.2, 10.9, 10.5],
            "humidity_pct": [65.0, 68.0, 70.0, 72.0, 74.0],
            "solar_irradiance_wm2": [0.0, 0.0, 0.0, 0.0, 0.0],
        })

    def test_predict_returns_numpy_array(self):
        preds = predict(self.sample_df)
        self.assertIsInstance(preds, np.ndarray)
        self.assertEqual(len(preds), len(self.sample_df))

    def test_predict_values_are_finite(self):
        preds = predict(self.sample_df)
        self.assertFalse(np.isnan(preds).any(), "Predictions contain NaN")
        self.assertFalse(np.isinf(preds).any(), "Predictions contain Inf")

    def test_preserves_row_order_and_count(self):
        # Permute dataframe
        reversed_df = self.sample_df.iloc[::-1].reset_index(drop=True)
        preds_normal = predict(self.sample_df)
        preds_reversed = predict(reversed_df)

        self.assertEqual(len(preds_normal), len(preds_reversed))
        # First row of reversed should match last row of normal
        self.assertAlmostEqual(preds_normal[-1], preds_reversed[0], places=3)

    def test_missing_column_raises_error(self):
        invalid_df = self.sample_df.drop(columns=["solar_irradiance_wm2"])
        with self.assertRaises(ValueError):
            predict(invalid_df)

    def test_empty_dataframe_returns_empty_array(self):
        empty_df = pd.DataFrame(columns=["timestamp", "ambient_temp_c", "humidity_pct", "solar_irradiance_wm2"])
        preds = predict(empty_df)
        self.assertEqual(len(preds), 0)

    def test_null_values_raise_error(self):
        null_df = self.sample_df.copy()
        null_df.loc[1, "ambient_temp_c"] = np.nan
        with self.assertRaises(ValueError):
            predict(null_df)


if __name__ == "__main__":
    unittest.main()
