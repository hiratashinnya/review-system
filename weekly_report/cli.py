"""CLI entry point for read-only collection and annotated report rendering."""

import argparse
from datetime import datetime
from pathlib import Path
import subprocess
import sys

from . import analysis, output, snapshot
from .github import normalize_repository
from .local import resolve_root
from .period import JST, resolve_period


def _page_limit(raw):
    value = int(raw)
    if value < 2:
        raise argparse.ArgumentTypeError("--max-pages は 2 以上を指定してください")
    return value


def parser():
    command = argparse.ArgumentParser(prog="python3 -B -m weekly_report", description="週次レポート")
    commands = command.add_subparsers(dest="action", required=True)
    collect = commands.add_parser("collect", help="GitHub と作業ツリーを読み取り定量集計を保存")
    collect.add_argument("--repository", required=True, help="GitHub OWNER/REPO")
    collect.add_argument("--base-ref", default="origin/main", help="観測時に解決するローカル基準 ref")
    collect.add_argument("--start", help="期間の開始 (ISO 8601、オフセット省略時 JST)")
    collect.add_argument("--end", help="期間の終了 (ISO 8601、オフセット省略時 JST)")
    collect.add_argument("--now", help="期間イベントの基準時刻を固定 (ISO 8601、テスト・再現用)")
    collect.add_argument("--previous", help="比較する前回 snapshot.json")
    collect.add_argument("--max-pages", default=30, type=_page_limit, help="各 API 応答の検証上限")
    render = commands.add_parser("render", help="snapshot を再使用して分析付き HTML と要約を保存")
    render.add_argument("--snapshot", required=True)
    render.add_argument("--analysis", required=True, help="Skill が作る分析 JSON")
    for action in (collect, render):
        action.add_argument("--out", help="作業ツリー外の新規出力先（省略時は一時ディレクトリ）")
    return command


def _previous(path):
    if path is None:
        return None
    try:
        data = snapshot.load(path)
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        root = resolve_root(Path.cwd())
        interpretation = None
        if args.action == "collect":
            observed_at = datetime.now(JST)
            period = resolve_period(args.start, args.end, args.now, observed_at=observed_at)
            repository = normalize_repository(args.repository)
            previous = _previous(args.previous)
            data = snapshot.collect(root, repository, args.base_ref, period, args.max_pages, previous,
                                    observed_at=observed_at)
        else:
            data = snapshot.load(args.snapshot)
            if data["schema_version"] != snapshot.SCHEMA_VERSION:
                raise ValueError("snapshot の版に対応していません")
            interpretation = analysis.validate(snapshot.load(args.analysis))
        destination = output.write(data, interpretation, args.out, root)
    except (OSError, ValueError, TypeError, AttributeError, KeyError, subprocess.TimeoutExpired) as exc:
        print(f"weekly_report: {exc}", file=sys.stderr)
        return 1
    print(destination)
    return 0
