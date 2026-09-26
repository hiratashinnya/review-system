"""Issue #539 の保守性原則を検査する read-only lint。"""

from .scanner import build_baseline, scan

__all__ = ["build_baseline", "scan"]
