"""Define the defect metrics command-line interface."""

import argparse
from .collect import DEFAULT_FETCH_LIMIT
from .model import DEFAULT_REPORT_WINDOW


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python3 -m defect_metrics",
        description="欠陥混入率（派生 Issue/PR）の指標を算出する（Issue #488）",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    def add_common(target: argparse.ArgumentParser) -> None:
        target.add_argument(
            "--repository",
            required=True,
            help="OWNER/REPO（取得先であると同時に、本文中のリポジトリ修飾付き参照"
            "＝OWNER/REPO#N と完全 URL を自リポジトリのものだけに絞る判定にも使う・"
            "Issue #493。形式が読めなければ窓内 Issue の有無に依らず exit 1）",
        )
        target.add_argument("--issues-json", help="gh issue list --json 出力（省略時は gh を実行）")
        target.add_argument("--pulls-json", help="gh pr list --json 出力（省略時は gh を実行）")
        target.add_argument(
            "--limit", type=int, default=DEFAULT_FETCH_LIMIT, help="gh list の --limit"
        )

    report = sub.add_parser("report", help="レポート JSON を出力する")
    add_common(report)
    report.add_argument("--window-start", help="窓の開始（ISO8601・UTC・含む）")
    report.add_argument("--window-end", help="窓の終了（ISO8601・UTC・含まない）")
    report.add_argument(
        "--window-days",
        type=float,
        default=DEFAULT_REPORT_WINDOW.total_seconds() / 86400.0,
        help="窓の幅（日）。両端を省略したときは --now を終端に使う",
    )
    report.add_argument("--now", help="現在時刻を固定する（省略時のみ wall clock を読む）")
    report.add_argument("--output", help="出力先ファイル（省略時は stdout）")

    verify = sub.add_parser(
        "verify-baseline",
        help="基線窓の実測値（Issue #488「現状と根拠」）を再現できるか照合する",
    )
    add_common(verify)

    return parser
