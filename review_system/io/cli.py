"""合成ルート＝`reviewer` CLI。design/03。引数→ドメイン型→core→レンダリング。

MVP コマンド：version／review（P1＋🤖自動適用→HTML）／revert／feedback。
承認/決定/FB は **レポートのパスだけ**を取り、review_id で同梱 feedback.json／commits を解決
（DD10/DD14）。診断は stderr、結果は stdout（DD9）。実 PF は --findings（Claude が書いた
findings.json＝PF 駆動 MVP の実体）。無指定は空 findings（配線確認用）。
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from ..domain.enums import DocumentType
from ..domain.ids import Scope, ExecutionId
from ..domain.review import SourceFile
from ..domain.result import Success, Failure
from ..ports.platform import ReviewRequest, RawReviewResponse
from ..adapters.fake import FakePlatformAdapter
from ..adapters.file_platform import FilePlatformAdapter
from ..adapters.guard import GuardingPlatform
from ..parsing.lint import SUPPORTED_CRITERIA_MAJOR, SUPPORTED_POLICY_MAJOR
from ..prompts.registry import TEMPLATE_VERSIONS
from ..persistence.criteria_repo import discover_criteria, load_policy_file
from ..persistence.workspace_git import GitWorkspaceRepository
from ..persistence.feedback_store import append_feedback
from ..core.pipeline import Deps, run_review
from ..core.apply import apply_auto
from .report_html import render_html

EXIT_OK, EXIT_BADREQ, EXIT_FAILCLOSE = 0, 2, 3
WORKSPACE = Path(".review-workspace")
STATE = Path(".review-state")
_RID = re.compile(r'data-review-id="([^"]+)"')


def _now() -> str:
    """microseconds 精度の UTC ISO 文字列（同一秒内の review_id 衝突を避ける・#5）。"""
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="reviewer")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("version", help="対応する基準/ポリシー MAJOR・プロンプト雛形版を表示")

    p = sub.add_parser("review", help="P1 通し＋🤖自動適用→HTML レポート")
    p.add_argument("paths", nargs="+")
    p.add_argument("--ref", action="append", default=[])
    p.add_argument("--type", dest="type_", choices=[d.value for d in DocumentType])
    p.add_argument("--criteria", default="criteria/org")
    p.add_argument("--policy", default="criteria/policy/org.yaml")
    p.add_argument("--findings", help="Claude が書いた findings.json（PF 駆動の実体）")
    p.add_argument("--out", default="report.html")

    r = sub.add_parser("revert", help="レポートのパスから review を revert")
    r.add_argument("report")

    f = sub.add_parser("feedback", help="レポートのパスから feedback.json を DS5 に記録")
    f.add_argument("report")

    args = parser.parse_args(argv)
    return {"version": lambda: _cmd_version(),
            "review": lambda: _cmd_review(args),
            "revert": lambda: _cmd_revert(args),
            "feedback": lambda: _cmd_feedback(args)}.get(args.cmd, lambda: EXIT_BADREQ)()


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
    adapter = (FilePlatformAdapter(Path(args.findings)) if args.findings
               else FakePlatformAdapter(RawReviewResponse((), ())))
    platform = GuardingPlatform(adapter)        # PF 境界のガード（例外→fail-close・M1）
    deps = Deps(
        platform=platform,
        load_criteria=lambda dt, sc: discover_criteria(Path(args.criteria), dt, sc),
        load_policy=lambda sc: load_policy_file(Path(args.policy)),
        now=_now,
    )
    match run_review(request, deps):
        case Failure(notice):
            print(f"O-14 [{notice.stage.value}] {notice.reason} -> {notice.next_action}",
                  file=sys.stderr)
            return EXIT_FAILCLOSE
        case Success(report):
            pass
    # 🤖 自動適用（finding 単位コミット・S4）。失敗時は書込ゼロで O-14
    if report.auto:
        targets = {str(sf.path): sf.content for sf in request.targets}
        out = apply_auto(report.stamp.execution_id, report.auto, targets,
                         GitWorkspaceRepository(WORKSPACE), deps.now())
        match out:
            case Failure(notice):
                print(f"O-14 [apply] {notice.reason} -> {notice.next_action}", file=sys.stderr)
                return EXIT_FAILCLOSE
            case Success(commits):
                _save_commits(report.stamp.execution_id.value, [c.commit_ref for c in commits])
    Path(args.out).write_text(render_html(report), encoding="utf-8")
    print(args.out)
    return EXIT_OK


def _cmd_revert(args) -> int:
    rid = _review_id_of(Path(args.report))
    if rid is None:
        print("error: レポートから review_id を読めない", file=sys.stderr)
        return EXIT_BADREQ
    try:                                        # #12 T3/T5：壊れた state ファイルもクラッシュさせず fail-close
        refs = _load_commits(rid)
    except (json.JSONDecodeError, UnicodeDecodeError, OSError) as e:
        print(f"O-14 [apply] commits 状態ファイルを読めない: {e} "
              f"-> .review-state の当該 .commits.json を確認のこと", file=sys.stderr)
        return EXIT_FAILCLOSE
    if not isinstance(refs, list) or not all(isinstance(r, str) for r in refs):  # #12 T4
        print(f"O-14 [apply] commits 状態ファイルの形式が不正: {refs!r} "
              f"-> .review-state の当該 .commits.json を確認のこと", file=sys.stderr)
        return EXIT_FAILCLOSE
    if not refs:
        print("revert 対象なし", file=sys.stderr)
        return EXIT_BADREQ
    repo = GitWorkspaceRepository(WORKSPACE)
    exec_id = ExecutionId(rid)
    for ref in reversed(refs):                  # 新しい順に戻す
        try:                                    # #10：git 失敗（衝突/不正 ref/workdir 破損）を fail-close
            repo.revert(exec_id, ref)
        except (subprocess.CalledProcessError, OSError) as e:
            detail = getattr(e, "stderr", None) or getattr(e, "stdout", None) or e  # #12 T2：git の実エラーを O-14 に
            print(f"O-14 [apply] revert に失敗（{ref}）: {str(detail).strip()} "
                  f"-> 一部のみ revert された可能性。ワークスペースを手動確認のこと",
                  file=sys.stderr)
            return EXIT_FAILCLOSE
    print(f"reverted {len(refs)} commit(s) for {rid}")
    return EXIT_OK


def _cmd_feedback(args) -> int:
    report = Path(args.report)
    rid = _review_id_of(report)
    if rid is None:
        print("error: レポートから review_id を読めない", file=sys.stderr)
        return EXIT_BADREQ
    fb_path = report.parent / f"{rid}.feedback.json"
    if not fb_path.exists():
        print(f"error: {fb_path.name} が無い（HTML で書き出して同ディレクトリに置く）", file=sys.stderr)
        return EXIT_BADREQ
    try:                                          # #6：壊れた JSON で落ちない
        data = json.loads(fb_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        print(f"error: feedback.json を読めない: {e}", file=sys.stderr)
        return EXIT_BADREQ
    if not isinstance(data, dict) or data.get("review_id") != rid:   # #6：別 review 誤取込を防ぐ
        print("error: feedback.json の review_id がレポートと一致しない", file=sys.stderr)
        return EXIT_BADREQ
    try:                                          # #6/#7：item のキー欠落は BADREQ
        n = append_feedback(STATE / "feedback.jsonl", rid, data.get("feedback", []))
    except (ValueError, TypeError) as e:
        print(f"error: feedback の内容が不正: {e}", file=sys.stderr)
        return EXIT_BADREQ
    print(f"recorded {n} feedback item(s)")
    return EXIT_OK


def _review_id_of(report: Path) -> str | None:
    m = _RID.search(report.read_text(encoding="utf-8"))
    return m.group(1) if m else None


def _commits_path(rid: str) -> Path:
    safe = re.sub(r"[^A-Za-z0-9._-]", "-", rid)
    return STATE / f"{safe}.commits.json"


def _save_commits(rid: str, refs: list[str]) -> None:
    STATE.mkdir(parents=True, exist_ok=True)
    _commits_path(rid).write_text(json.dumps(refs), encoding="utf-8")


def _load_commits(rid: str) -> list[str]:
    p = _commits_path(rid)
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else []


if __name__ == "__main__":
    raise SystemExit(main())
