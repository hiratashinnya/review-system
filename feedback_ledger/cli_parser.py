"""Build the feedback ledger command parser."""

from __future__ import annotations

import argparse

from .cli_parser_proposal import register_proposal_decisions
from .cli_parser_reports import register_report_commands
from .cli_parser_triage import register_triage_commands
from .cli_parser_write import register_write_commands


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="feedback_ledger",
        description="オーナー判断フィードバック台帳（.ai/feedback/）の CLI 専用書込みと機械 lint",
    )
    parser.add_argument(
        "--root", default=None,
        help="repo root（既定＝このパッケージを含むリポジトリ）",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    register_write_commands(sub)
    register_proposal_decisions(sub)
    register_triage_commands(sub)
    register_report_commands(sub)
    return parser
