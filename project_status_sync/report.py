"""公開 report API の互換入口。"""

from .report_data import build_report, is_red
from .report_summary import render_summary

__all__ = ("build_report", "is_red", "render_summary")
