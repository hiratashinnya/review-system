"""Fixed defect metric and report definitions."""

from datetime import datetime, timedelta, timezone
from .types import Window


#: レポート JSON の読取側パース互換の版。据置理由は defect_metrics/README.md §2.2。
SCHEMA_VERSION = 1


DERIVATION_HORIZON = timedelta(hours=72)


DEFAULT_REPORT_WINDOW = timedelta(days=7)


TRAILING_WINDOW = timedelta(days=28)


REGRESSION_FACTOR = 1.5


RATIO_DIGITS = 2


BASELINE_WINDOW = Window(
    start=datetime(2026, 8, 2, tzinfo=timezone.utc),
    end=datetime(2026, 8, 16, tzinfo=timezone.utc),
)


BASELINE_MERGED_PRS = 22


BASELINE_ALL_ISSUES = 41


BASELINE_DERIVED_ISSUES = 15


BASELINE_ISSUES_PER_PR = 1.86


BASELINE_DERIVED_PER_PR = 0.68
