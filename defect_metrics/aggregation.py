"""Compatibility exports for window metric calculations."""

from .calculation import compute_window_metrics, is_derived
from .metric_values import WindowMetrics, _ratio, _rounded

__all__ = ["WindowMetrics", "is_derived", "compute_window_metrics"]
