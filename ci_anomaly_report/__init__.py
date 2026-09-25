"""GitHub Actions の異常を SessionStart 配送用レポートへ集約する。"""

from .collector import collect_report

__all__ = ["collect_report"]
