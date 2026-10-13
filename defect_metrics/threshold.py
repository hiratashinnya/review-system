"""閾値判定の互換 export。選択と根拠は ``defect_metrics/README.md`` §3 を参照。"""

from .metrics import WindowMetrics
from .model import BASELINE_DERIVED_PER_PR, RATIO_DIGITS, REGRESSION_FACTOR
from .threshold_evaluate import evaluate
from .threshold_types import Alert, Evaluation, Skip, BASELINE_EXCEEDED, TRAILING_REGRESSION, TRAILING_AGGREGATION, TRAILING_AGGREGATION_DETAIL, SKIP_NO_DENOMINATOR, SKIP_NO_TRAILING_DATA

__all__ = [
    "WindowMetrics",
    "BASELINE_DERIVED_PER_PR",
    "RATIO_DIGITS",
    "REGRESSION_FACTOR",
    "Alert",
    "Evaluation",
    "Skip",
    "BASELINE_EXCEEDED",
    "TRAILING_REGRESSION",
    "TRAILING_AGGREGATION",
    "TRAILING_AGGREGATION_DETAIL",
    "SKIP_NO_DENOMINATOR",
    "SKIP_NO_TRAILING_DATA",
    "evaluate",
]
