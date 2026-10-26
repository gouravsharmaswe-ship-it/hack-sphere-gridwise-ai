"""Gridwise AI - Shared Deterministic Dispatch and Overload Rule Engine.

Rules Specification (HackSphere 3.0):
1. Renewable Storage Mode:
   - Predicted demand is strictly greater than 160 kW (> 160.0), OR
   - Timestamp's local hour is from 18 through 22 inclusive (18 <= hour <= 22).

2. Main Grid Mode:
   - Selected ONLY when predicted demand <= 160.0 kW AND timestamp's local hour is outside 18-22.

3. Critical Overload Alert:
   - Independently triggered whenever predicted demand is >= 200.0 kW.
   - Independent of dispatch mode (a reading can be Renewable Storage Mode AND have Critical Overload Alert).

Note: These are decision-support rules, not authorization to control real physical electrical equipment.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Union
import zoneinfo

RENEWABLE_STORAGE_THRESHOLD_KW: float = 160.0
CRITICAL_OVERLOAD_THRESHOLD_KW: float = 200.0
PEAK_HOURS_START: int = 18
PEAK_HOURS_END: int = 22

DISPATCH_MODE_RENEWABLE_STORAGE = "Renewable Storage Mode"
DISPATCH_MODE_MAIN_GRID = "Main Grid Mode"


@dataclass(frozen=True)
class DispatchEvaluation:
    timestamp: str
    local_hour: int
    predicted_demand_kw: float
    dispatch_mode: str
    is_peak_hour: bool
    is_demand_exceeding_160: bool
    is_critical_overload: bool
    reason: str


def parse_timestamp_hour(ts: Union[str, datetime], tz_str: str = "UTC") -> int:
    """Extracts the integer hour (0-23) in the specified timezone."""
    if isinstance(ts, str):
        # Format can be 'YYYY-MM-DD HH:MM:SS' or ISO format
        # Replace space or T
        clean_ts = ts.strip().replace("T", " ")
        if "+" in clean_ts:
            dt = datetime.fromisoformat(ts)
        elif clean_ts.endswith("Z"):
            dt = datetime.fromisoformat(clean_ts.replace("Z", "+00:00"))
        else:
            # Assume local format YYYY-MM-DD HH:MM:SS
            dt = datetime.strptime(clean_ts[:19], "%Y-%m-%d %H:%M:%S")
            tz = zoneinfo.ZoneInfo(tz_str)
            dt = dt.replace(tzinfo=tz)
    else:
        dt = ts

    if dt.tzinfo is not None and tz_str != "UTC":
        dt = dt.astimezone(zoneinfo.ZoneInfo(tz_str))

    return dt.hour


def evaluate_dispatch(
    predicted_demand_kw: float,
    timestamp: Union[str, datetime],
    tz_str: str = "UTC",
) -> DispatchEvaluation:
    """Evaluates dispatch mode and overload status for a given prediction and timestamp."""
    demand = float(predicted_demand_kw)
    hour = parse_timestamp_hour(timestamp, tz_str=tz_str)
    ts_str = timestamp if isinstance(timestamp, str) else timestamp.strftime("%Y-%m-%d %H:%M:%S")

    is_peak = (PEAK_HOURS_START <= hour <= PEAK_HOURS_END)
    is_demand_high = (demand > RENEWABLE_STORAGE_THRESHOLD_KW)
    is_overload = (demand >= CRITICAL_OVERLOAD_THRESHOLD_KW)

    # Dispatch mode logic
    reasons = []
    if is_demand_high and is_peak:
        dispatch_mode = DISPATCH_MODE_RENEWABLE_STORAGE
        reasons.append(f"Demand ({demand:.2f} kW > 160 kW) and Peak Hours ({hour:02d}:00 in 18-22)")
    elif is_demand_high:
        dispatch_mode = DISPATCH_MODE_RENEWABLE_STORAGE
        reasons.append(f"Demand ({demand:.2f} kW > 160 kW threshold)")
    elif is_peak:
        dispatch_mode = DISPATCH_MODE_RENEWABLE_STORAGE
        reasons.append(f"Peak evening load window ({hour:02d}:00 in 18:00-22:00)")
    else:
        dispatch_mode = DISPATCH_MODE_MAIN_GRID
        reasons.append(f"Standard operation: Demand ({demand:.2f} kW <= 160 kW) outside peak hours")

    if is_overload:
        reasons.append(f"CRITICAL OVERLOAD ALERT: Predicted demand {demand:.2f} kW >= 200 kW")

    return DispatchEvaluation(
        timestamp=ts_str,
        local_hour=hour,
        predicted_demand_kw=demand,
        dispatch_mode=dispatch_mode,
        is_peak_hour=is_peak,
        is_demand_exceeding_160=is_demand_high,
        is_critical_overload=is_overload,
        reason="; ".join(reasons),
    )
