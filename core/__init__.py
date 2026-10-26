"""Core package for Gridwise AI."""
from .dispatch_rules import (
    evaluate_dispatch,
    DispatchEvaluation,
    DISPATCH_MODE_RENEWABLE_STORAGE,
    DISPATCH_MODE_MAIN_GRID,
    RENEWABLE_STORAGE_THRESHOLD_KW,
    CRITICAL_OVERLOAD_THRESHOLD_KW,
    PEAK_HOURS_START,
    PEAK_HOURS_END,
)

__all__ = [
    "evaluate_dispatch",
    "DispatchEvaluation",
    "DISPATCH_MODE_RENEWABLE_STORAGE",
    "DISPATCH_MODE_MAIN_GRID",
    "RENEWABLE_STORAGE_THRESHOLD_KW",
    "CRITICAL_OVERLOAD_THRESHOLD_KW",
    "PEAK_HOURS_START",
    "PEAK_HOURS_END",
]
