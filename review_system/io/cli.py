"""合成ルート＝`reviewer` CLI。design/03。引数→ドメイン型→core→レンダリング。

MVP：`version`（版定数を表示）と `review`（P1 通し→HTML レポート）。実 PF アダプタ
（ClaudeCodeAdapter / stdout 駆動）は未実装のため、既定 platform は空findings を返す
プレースホルダ（配線の確認用）。診断は stderr、結果（パス）は stdout（DD9）。
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

from ..domain.enums import DocumentType
from ..domain.ids import Scope
from ..domain.review import SourceFile
from ..domain.result import Success, Failure
from ..ports.platform import ReviewRequest, RawReviewResponse
from ..adapters.fake import FakePlatformAdapter
from ..parsing.lint import SUPPORTED_CRITERIA_MAJOR, SUPPORTED_POLICY_MAJOR
from ..prompts.registry import TEMPLATE_VERSIONS
from ..persistence.criteria_repo import discover_criteria, load_policy_file
from ..core.pipeline import Deps, run_review
from .report_html import render_html

EXIT_OK, EXIT_BADREQ, EXIT_FAILCLOSE = 0, 2, 3


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="reviewer")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("version", help="対応する基準/ポリシー MAJOR・プロンプト雛形版を表示")

    p = sub.add_parser("review", help="P1 通し→HTML レポート")
    p.add_argument("paths", nargs="+")
    p.add_argument("--ref", action="append", default=[])
    p.add_argument("--type", dest="type_", choices=[d.value for d in DocumentType])
    p.add_argument("--criteria", default="criteria/org")
    p.add_argument("--policy", default="criteria/policy/org.yaml")
    p.add_argument("--out", default="report.html")

    args = parser.parse_args(argv)
    if args.cmd == "version":
        return _cmd_version()
    if args.cmd == "review":
        return _cmd_review(args)
    return EXIT_BADREQ


def _cmd_version() -> int:
    print(f"criteria MAJOR supported: {sorted(SUPPORTED_CRITERIA_MAJOR)}")
    print(f"policy   MAJOR supported: {sorted(SUPPORTED_POLICY_MAJOR)}")
    print("prompt templates:")
    for name, ver in TEMPLATE_VERSIONS.items():
        print(f"  {name}: {ver}")
    return EXIT_OK


def _read(p: str) -> SourceFile:
    path = Path(p)
    return SourceFile(path=path, content=path.read_text(encoding="utf-8"))


def _cmd_review(args) -> int:
    if not args.type_:
        print("error: --type が必要（MVP は AI 型推定なし）", file=sys.stderr)
        return EXIT_BADREQ
    request = ReviewRequest(
        targets=tuple(_read(p) for p in args.paths),
        references=tuple(_read(p) for p in args.ref),
        type_override=DocumentType(args.type_),
        scope=Scope.org(),
    )
    criteria_dir, policy_path = Path(args.criteria), Path(args.policy)
    deps = Deps(
        platform=_make_platform(),
        load_criteria=lambda dt, sc: discover_criteria(criteria_dir, dt, sc),
        load_policy=lambda sc: load_policy_file(policy_path),
        now=lambda: datetime.now(timezone.utc).isoformat(timespec="seconds"),
    )
    outcome = run_review(request, deps)
    match outcome:
        case Success(report):
            Path(args.out).write_text(render_html(report), encoding="utf-8")
            print(args.out)                              # 結果＝stdout（レポートのパス）
            return EXIT_OK
        case Failure(notice):
            print(f"O-14 [{notice.stage.value}] {notice.reason} -> {notice.next_action}",
                  file=sys.stderr)
            return EXIT_FAILCLOSE
    return EXIT_BADREQ


def _make_platform():
    """MVP プレースホルダ：空 findings を返す。実 PF アダプタは後続（stdout 駆動 / ClaudeCode）。"""
    return FakePlatformAdapter(RawReviewResponse((), ()))


if __name__ == "__main__":
    raise SystemExit(main())
