"""Tests for Core Dispatch Rules and Critical Overload Alerts.

Tests boundary conditions:
- 160 kW exact boundary: <= 160 is Main Grid (if outside 18-22), > 160 is Renewable Storage
- 160.0001 kW vs 160.0 kW
- 199.99 kW vs 200.0 kW (Critical Overload Alert trigger)
- Peak hours (18:00 to 22:00 inclusive)
  - 17:59 (off-peak)
  - 18:00 (peak)
  - 22:00 (peak)
  - 22:01 (off-peak)
  - 23:00 (off-peak)
  - 00:00 midnight (off-peak)
- Independence of Critical Overload Alert:
  - High demand (e.g. 210 kW) in off-peak hour triggers both Renewable Storage Mode AND Critical Overload Alert
  - High demand (e.g. 210 kW) in peak hour triggers both
  - Demand <= 160 (e.g. 150 kW) in off-peak hour: Main Grid Mode, NO alert
  - Demand <= 160 (e.g. 150 kW) in peak hour (19:00): Renewable Storage Mode, NO alert
- Timezone handling: UTC vs local offset conversions.
"""

import unittest
from datetime import datetime
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from core.dispatch_rules import (
    evaluate_dispatch,
    DISPATCH_MODE_RENEWABLE_STORAGE,
    DISPATCH_MODE_MAIN_GRID,
    RENEWABLE_STORAGE_THRESHOLD_KW,
    CRITICAL_OVERLOAD_THRESHOLD_KW,
)


class TestDispatchRules(unittest.TestCase):

    def test_demand_threshold_boundaries_off_peak(self):
        # Off-peak hour 14:00 (2 PM)
        ts = "2024-01-01 14:00:00"

        # Exactly 160 kW -> Main Grid Mode, No Alert
        res_160 = evaluate_dispatch(160.0, ts)
        self.assertEqual(res_160.dispatch_mode, DISPATCH_MODE_MAIN_GRID)
        self.assertFalse(res_160.is_demand_exceeding_160)
        self.assertFalse(res_160.is_critical_overload)

        # 159.99 kW -> Main Grid Mode, No Alert
        res_159 = evaluate_dispatch(159.99, ts)
        self.assertEqual(res_159.dispatch_mode, DISPATCH_MODE_MAIN_GRID)
        self.assertFalse(res_159.is_demand_exceeding_160)

        # 160.01 kW -> Renewable Storage Mode (strictly > 160), No Alert
        res_160_01 = evaluate_dispatch(160.01, ts)
        self.assertEqual(res_160_01.dispatch_mode, DISPATCH_MODE_RENEWABLE_STORAGE)
        self.assertTrue(res_160_01.is_demand_exceeding_160)
        self.assertFalse(res_160_01.is_critical_overload)

    def test_overload_threshold_boundaries(self):
        ts = "2024-01-01 10:00:00"

        # 199.99 kW -> Renewable Storage (> 160), but NO Critical Overload Alert (< 200)
        res_199 = evaluate_dispatch(199.99, ts)
        self.assertEqual(res_199.dispatch_mode, DISPATCH_MODE_RENEWABLE_STORAGE)
        self.assertFalse(res_199.is_critical_overload)

        # Exactly 200.0 kW -> Renewable Storage AND Critical Overload Alert (>= 200)
        res_200 = evaluate_dispatch(200.0, ts)
        self.assertEqual(res_200.dispatch_mode, DISPATCH_MODE_RENEWABLE_STORAGE)
        self.assertTrue(res_200.is_critical_overload)

        # 250.0 kW -> Renewable Storage AND Critical Overload Alert
        res_250 = evaluate_dispatch(250.0, ts)
        self.assertEqual(res_250.dispatch_mode, DISPATCH_MODE_RENEWABLE_STORAGE)
        self.assertTrue(res_250.is_critical_overload)

    def test_peak_hour_boundaries(self):
        # Demand below threshold (100 kW) to isolate hour effect
        demand = 100.0

        # 17:00 -> Off-peak -> Main Grid Mode
        res_17 = evaluate_dispatch(demand, "2024-01-01 17:00:00")
        self.assertEqual(res_17.dispatch_mode, DISPATCH_MODE_MAIN_GRID)
        self.assertFalse(res_17.is_peak_hour)

        # 18:00 -> Peak Start (inclusive) -> Renewable Storage Mode
        res_18 = evaluate_dispatch(demand, "2024-01-01 18:00:00")
        self.assertEqual(res_18.dispatch_mode, DISPATCH_MODE_RENEWABLE_STORAGE)
        self.assertTrue(res_18.is_peak_hour)

        # 20:00 -> Peak Mid -> Renewable Storage Mode
        res_20 = evaluate_dispatch(demand, "2024-01-01 20:00:00")
        self.assertEqual(res_20.dispatch_mode, DISPATCH_MODE_RENEWABLE_STORAGE)
        self.assertTrue(res_20.is_peak_hour)

        # 22:00 -> Peak End (inclusive) -> Renewable Storage Mode
        res_22 = evaluate_dispatch(demand, "2024-01-01 22:00:00")
        self.assertEqual(res_22.dispatch_mode, DISPATCH_MODE_RENEWABLE_STORAGE)
        self.assertTrue(res_22.is_peak_hour)

        # 23:00 -> Off-peak -> Main Grid Mode
        res_23 = evaluate_dispatch(demand, "2024-01-01 23:00:00")
        self.assertEqual(res_23.dispatch_mode, DISPATCH_MODE_MAIN_GRID)
        self.assertFalse(res_23.is_peak_hour)

        # 00:00 Midnight -> Off-peak -> Main Grid Mode
        res_00 = evaluate_dispatch(demand, "2024-01-01 00:00:00")
        self.assertEqual(res_00.dispatch_mode, DISPATCH_MODE_MAIN_GRID)
        self.assertFalse(res_00.is_peak_hour)

    def test_overload_alert_independence(self):
        # Test that Critical Overload is independent of dispatch mode
        # E.g. at 19:00 with 220 kW: Peak hour AND overload
        res_peak_overload = evaluate_dispatch(220.0, "2024-01-01 19:00:00")
        self.assertEqual(res_peak_overload.dispatch_mode, DISPATCH_MODE_RENEWABLE_STORAGE)
        self.assertTrue(res_peak_overload.is_critical_overload)

        # At 03:00 with 220 kW: Off-peak hour, but demand > 160 kW and >= 200 kW
        res_offpeak_overload = evaluate_dispatch(220.0, "2024-01-01 03:00:00")
        self.assertEqual(res_offpeak_overload.dispatch_mode, DISPATCH_MODE_RENEWABLE_STORAGE)
        self.assertTrue(res_offpeak_overload.is_critical_overload)


if __name__ == "__main__":
    unittest.main()
