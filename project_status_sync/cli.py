"""`python3 -m project_status_sync sync` の入口。

stdout は `$GITHUB_STEP_SUMMARY` 用の markdown、stderr は1行要約、
`--report` に JSON を必ず書く（中断時も書く——workflow は publish してから
job を赤くする順序を守るため、レポートが残らないまま落ちてはならない）。

exit code:
  0  … 変更の有無に関わらず正常（警告なし）
  20 … 中断または警告あり（CI を赤くする。report は書けている）
  2  … 引数・入出力の失敗（argparse / report 書込不能）
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from typing import Any, Callable, Sequence, TextIO

from .github import ProjectStatusClient, ProjectSyncApiError, resolve_token
from .model import (
    Abort,
    MAX_SNAPSHOT_AGE_SECONDS,
    Plan,
    PlannedChange,
    ProjectView,
    WRITABLE_TARGETS,
)
from .planner import build_plan, check_snapshot
from .report import build_report, is_red, render_summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="project-status-sync")
    subparsers = parser.add_subparsers(dest="command", required=True)
    sync = subparsers.add_parser(
        "sync", help="blocker snapshot から Project の Status を同期する"
    )
    sync.add_argument("--repository", required=True, metavar="OWNER/REPO")
    sync.add_argument("--project-id", required=True, metavar="PVT_...")
    sync.add_argument(
        "--project-number",
        type=int,
        default=None,
        help="指定すると Project の number を照合する（別 Project への誤書き込み防止）",
    )
    sync.add_argument("--snapshot", required=True, type=Path)
    sync.add_argument("--report", required=True, type=Path)
    sync.add_argument(
        "--max-age-seconds", type=int, default=MAX_SNAPSHOT_AGE_SECONDS
    )
    sync.add_argument(
        "--apply",
        action="store_true",
        help="実際に Project へ書き込む。既定は dry-run（計画のみ）",
    )
    return parser


def _load_snapshot(path: Path) -> tuple[Any, Abort | None]:
    try:
        return json.loads(path.read_text(encoding="utf-8")), None
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return None, Abort("SNAPSHOT_INVALID", f"{type(exc).__name__}: {path}")


def run(
    argv: Sequence[str],
    *,
    stdout: TextIO,
    stderr: TextIO,
    client_factory: Callable[[], Any] | None = None,
    now: datetime | None = None,
) -> int:
    args = build_parser().parse_args(list(argv))
    current = now or datetime.now(timezone.utc)

    project: ProjectView | None = None
    snapshot: dict[str, Any] | None = None
    applied: list[PlannedChange] = []

    raw, load_abort = _load_snapshot(args.snapshot)
    if load_abort is not None:
        plan = Plan(abort=load_abort)
    else:
        # snapshot 単体で決まる fail-close（schema 不正 / degraded / 鮮度超過）は
        # Project API を1回も叩く前に確定させる。「degraded・鮮度超過なら1件も
        # 書かない」が検査ではなく実行順序で保証される。
        snapshot, snapshot_abort = check_snapshot(
            raw, now=current, max_age_seconds=args.max_age_seconds
        )
        if snapshot_abort is not None:
            plan = Plan(abort=snapshot_abort)
        else:
            assert snapshot is not None
            try:
                factory = client_factory or (
                    lambda: ProjectStatusClient(resolve_token())
                )
                client = factory()
                project = client.fetch_project(
                    args.project_id, args.repository, args.project_number
                )
            except ProjectSyncApiError as exc:
                plan = Plan(abort=Abort("PROJECT_UNREADABLE", exc.reason))
            else:
                plan = build_plan(snapshot, project.items, args.repository)
                if plan.abort is None and args.apply:
                    plan, applied = _apply(client, project, plan)

    report = build_report(
        repository=args.repository,
        project_id=args.project_id,
        project=project,
        snapshot=snapshot,
        plan=plan,
        applied=applied,
        apply_mode=bool(args.apply),
        now=current,
    )
    try:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(
            json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
            encoding="utf-8",
        )
    except OSError as exc:
        stderr.write(f"project-status-sync: report を書けない: {exc}\n")
        return 2

    stdout.write(render_summary(report))
    counts = report["counts"]
    stderr.write(
        "project-status-sync "
        f"{report['mode']} {args.repository} project#{report['project']['number']} "
        f"abort={(report['abort'] or {}).get('code', '-')} "
        f"planned={counts['planned']} applied={counts['applied']} "
        f"skipped={counts['skipped']} warnings={counts['warnings']}\n"
    )
    return 20 if is_red(report) else 0


def _apply(
    client: Any, project: ProjectView, plan: Plan
) -> tuple[Plan, list[PlannedChange]]:
    applied: list[PlannedChange] = []
    for change in plan.changes:
        if change.to_status not in WRITABLE_TARGETS:
            # 遷移先は Ready / Blocked に閉じている。ここへ来るのは planner の
            # 不具合なので、書かずに止める（`Done` を書かないことの最後の砦）。
            return (
                Plan(
                    changes=plan.changes,
                    skipped=plan.skipped,
                    warnings=plan.warnings,
                    abort=Abort(
                        "APPLY_FAILED",
                        f"{change.issue_ref}: 書き込み禁止の遷移先 {change.to_status!r}",
                    ),
                    considered=plan.considered,
                    out_of_scope=plan.out_of_scope,
                ),
                applied,
            )
        option_id = project.status_option_ids.get(change.to_status)
        if not option_id:
            return (
                Plan(
                    changes=plan.changes,
                    skipped=plan.skipped,
                    warnings=plan.warnings,
                    abort=Abort(
                        "APPLY_FAILED",
                        f"{change.issue_ref}: Status option {change.to_status!r} が Project に無い",
                    ),
                    considered=plan.considered,
                    out_of_scope=plan.out_of_scope,
                ),
                applied,
            )
        try:
            client.set_status(
                project.project_id, change.item_id, project.status_field_id, option_id
            )
        except ProjectSyncApiError as exc:
            return (
                Plan(
                    changes=plan.changes,
                    skipped=plan.skipped,
                    warnings=plan.warnings,
                    abort=Abort("APPLY_FAILED", f"{change.issue_ref}: {exc.reason}"),
                    considered=plan.considered,
                    out_of_scope=plan.out_of_scope,
                ),
                applied,
            )
        applied.append(change)
    return plan, applied


def main(argv: Sequence[str] | None = None) -> int:
    return run(
        sys.argv[1:] if argv is None else argv, stdout=sys.stdout, stderr=sys.stderr
    )
