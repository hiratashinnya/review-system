"""Owner-facing PR blocker report; this package never performs a merge."""

from .gate import PrMergeGateError, evaluate_owner_report

__all__ = ["PrMergeGateError", "evaluate_owner_report"]
