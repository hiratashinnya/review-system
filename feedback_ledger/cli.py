"""``python3 -m feedback_ledger …`` の CLI。

**`.ai/feedback/` へ書けるのはこの CLI だけ**という運用を前提にした verb 構成になっている
（人・エージェントの直接 Write/Edit は `.claude/settings.json` の ``permissions.deny`` で塞ぐ）。
下書きは版管理外の ``tmp/_feedback/`` に自由に書き、CLI が検証＋正規化して台帳へ落とす
（``karte ingest-review --from`` と同型）。

終了コード（``dsv2`` / ``karte`` と揃える）:
  ``0`` 正常 ／ ``2`` 未検出（指定した id・置き場が無い）／ ``4`` 前提違反・検証失敗

verb:
  ``new-entry --from``       下書きを検証・正規化して台帳エントリを新規作成する
  ``propose --from``         改訂案を新規作成する（``--supersede`` で旧案を superseded にする）
  ``amend-proposal --from``  ``pending`` の改訂案の本文を差し替える
  ``approve``                ``pending`` → ``approved``
  ``reject``                 ``pending`` → ``rejected``
  ``apply-done``             ``approved`` → ``applied``
  ``triage-open``            棚卸しの下書き（``tmp/_feedback/``）を生成する
  ``triage-close --from``    棚卸し記録を検証・正規化して確定する
  ``check [--canonical] [--require-base]``
                             機械 lint（L1〜L7／P1〜P4／T1）。``--require-base`` は
                             merge base を解決できないことを ERROR にする（CI 用）
  ``status [--now]``         導出状態と滞留
  ``index``                  文書の一覧

依存仕様: Issue #522「CLI verb」。
"""

from __future__ import annotations

import argparse
import datetime
import json
import sys
from pathlib import Path

from . import paths as paths_module
from . import schema as schema_module
from . import status as status_module
from .check import (
    check_canonical,
    check_id_references,
    check_paths_exist,
    check_proposals,
    check_triage,
    run_checks,
)
from .model import ERROR, WARN, DocumentError, Finding
from .paths import FeedbackMissing, FeedbackPathError
from .schema import PROPOSAL_SPEC, SPECS, TRIAGE_SPEC
from .store import Document, canonical_text, load_draft, load_store, write_document

EXIT_OK = 0
EXIT_NOT_FOUND = 2
EXIT_ERROR = 4

TRIAGE_DRAFT_TEMPLATE_VERDICT = "need-more-evidence"


def _parse_date(value: str) -> datetime.date:
    try:
        return datetime.date.fromisoformat(value)
    except ValueError:
        pass
    try:
        return datetime.datetime.fromisoformat(value).date()
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            f"ISO 8601 の日付/日時として読めない: {value!r}"
        ) from exc


def _print(findings, stream=None) -> None:
    handle = stream or sys.stdout
    for finding in findings:
        print(finding.render(), file=handle)


def _errors(findings) -> list[Finding]:
    return [finding for finding in findings if finding.level == ERROR]


def _preflight(root, spec, data, *, base_locus: str | None = None) -> list[Finding]:
    """書込み前に、確定後の姿でしか判定できない規則（L2/L3/P2〜P4/T1/L7）を先に掛ける。

    既存の別文書に起因する findings は**混ぜない**（locus 前方一致で絞る）。壊れた既存文書が
    あることを理由に新しいオーナー判断の記録を拒むと、価値経路を遮断する（PR6）。
    """
    store = load_store(root)
    relpath = f"{paths_module.FEEDBACK_DIRNAME}/{spec.subdir}/{data['id']}.toml"
    document = Document(
        kind=spec.kind,
        document_id=data["id"],
        relpath=relpath,
        path=Path(root) / relpath,
        data=data,
        text=canonical_text(spec, data),
    )
    others = [item for item in store.of(spec.kind) if item.document_id != data["id"]]
    store.documents[spec.kind] = sorted(others + [document], key=lambda item: item.relpath)
    findings = (
        check_paths_exist(store)
        + check_id_references(store)
        + check_proposals(store, None)
        + check_triage(store)
        + check_canonical(store)
    )
    locus = base_locus or relpath
    return [
        finding for finding in _errors(findings)
        if finding.locus == locus or finding.locus.startswith(f"{locus}::")
    ]


def _load_and_validate(root, spec, draft):
    data, findings = load_draft(root, spec, draft)
    if data is None:
        return None, findings
    return data, findings


def _fail(findings) -> int:
    _print(findings, stream=sys.stderr)
    return EXIT_ERROR


def _require_proposal(store, proposal_id):
    document = store.by_id(schema_module.PROPOSAL, proposal_id)
    if document is None:
        print(f"ERROR: 改訂案が見つからない: {proposal_id}", file=sys.stderr)
        return None
    return document


def _commit(root, spec, data) -> int:
    findings = _preflight(root, spec, data)
    if findings:
        return _fail(findings)
    with paths_module.writer_lock(root):
        target = write_document(root, spec, data)
    print(f"OK: {target.relative_to(Path(root).resolve()).as_posix()}")
    return EXIT_OK


# --- verbs ------------------------------------------------------------------


def cmd_new_entry(args) -> int:
    root = args.root
    spec = SPECS[schema_module.LEDGER]
    data, findings = _load_and_validate(root, spec, args.source)
    if data is None or _errors(findings):
        return _fail(findings)
    store = load_store(root)
    if store.by_id(schema_module.LEDGER, data["id"]) is not None:
        print(
            f"ERROR: [L6] 既存の台帳エントリは変更できない: {data['id']}"
            "（訂正は新しい id のエントリ＋supersedes で行う）",
            file=sys.stderr,
        )
        return EXIT_ERROR
    _print(findings)
    return _commit(root, spec, data)


def cmd_propose(args) -> int:
    root = args.root
    data, findings = _load_and_validate(root, PROPOSAL_SPEC, args.source)
    if data is None or _errors(findings):
        return _fail(findings)
    store = load_store(root)
    if store.by_id(schema_module.PROPOSAL, data["id"]) is not None:
        print(f"ERROR: 同じ id の改訂案が既にある: {data['id']}", file=sys.stderr)
        return EXIT_ERROR
    superseded = None
    if args.supersede:
        superseded = _require_proposal(store, args.supersede)
        if superseded is None:
            return EXIT_NOT_FOUND
        if superseded.data["status"] == "superseded":
            print(
                f"ERROR: [P1] 既に superseded の改訂案は再度 supersede できない: {args.supersede}",
                file=sys.stderr,
            )
            return EXIT_ERROR
    exit_code = _commit(root, PROPOSAL_SPEC, data)
    if exit_code != EXIT_OK or superseded is None:
        return exit_code
    replacement = dict(superseded.data)
    replacement["status"] = "superseded"
    with paths_module.writer_lock(root):
        write_document(root, PROPOSAL_SPEC, replacement)
    print(f"OK: {superseded.relpath} → status=superseded")
    return EXIT_OK


def cmd_amend_proposal(args) -> int:
    root = args.root
    data, findings = _load_and_validate(root, PROPOSAL_SPEC, args.source)
    if data is None or _errors(findings):
        return _fail(findings)
    store = load_store(root)
    current = _require_proposal(store, data["id"])
    if current is None:
        return EXIT_NOT_FOUND
    if current.data["status"] != "pending":
        print(
            f"ERROR: [P1] pending の改訂案だけを差し替えられる（現在: "
            f"{current.data['status']}）。決着済みの案は propose --supersede で置き換える",
            file=sys.stderr,
        )
        return EXIT_ERROR
    if data["status"] != "pending":
        print("ERROR: [P1] 差し替え後も status は pending でなければならない", file=sys.stderr)
        return EXIT_ERROR
    return _commit(root, PROPOSAL_SPEC, data)


def _decide(args, *, new_status, require_status="pending", updates=None) -> int:
    root = args.root
    store = load_store(root)
    document = _require_proposal(store, args.proposal)
    if document is None:
        return EXIT_NOT_FOUND
    if document.data["status"] != require_status:
        print(
            f"ERROR: [P1] {require_status} の改訂案にだけ実行できる"
            f"（現在: {document.data['status']}）",
            file=sys.stderr,
        )
        return EXIT_ERROR
    data = dict(document.data)
    data["status"] = new_status
    data.update(updates or {})
    return _commit(root, PROPOSAL_SPEC, data)


def cmd_approve(args) -> int:
    return _decide(args, new_status="approved", updates={
        "decided_in": args.triage,
        "decided_by": args.by,
        "decided_at": args.now or datetime.date.today(),
        "decision_reason": args.reason or "",
    })


def cmd_reject(args) -> int:
    return _decide(args, new_status="rejected", updates={
        "decided_in": args.triage or "",
        "decided_by": args.by,
        "decided_at": args.now or datetime.date.today(),
        "decision_reason": args.reason,
    })


def cmd_apply_done(args) -> int:
    return _decide(args, new_status="applied", require_status="approved", updates={
        "issue_ref": args.issue_ref,
        "applied_pr": args.applied_pr,
    })


def cmd_triage_open(args) -> int:
    root = args.root
    now = args.now or datetime.date.today()
    match = schema_module.TRIAGE_ID_RE.match(f"TRG-{args.week}")
    if match is None:
        print(
            f"ERROR: --week は YYYY-Wnn の形で指定する: {args.week!r}", file=sys.stderr
        )
        return EXIT_ERROR
    year = int(match.group("year"))
    week = int(match.group("week"))
    try:
        start = datetime.date.fromisocalendar(year, week, 1)
        end = datetime.date.fromisocalendar(year, week, 7)
    except ValueError:
        print(f"ERROR: 実在しない ISO 週: {args.week}", file=sys.stderr)
        return EXIT_ERROR

    store = load_store(root)
    entries = status_module.untriaged_ids(store, now)
    data = {
        "schema": TRIAGE_SPEC.schema_const,
        "id": f"TRG-{args.week}",
        "period_start": start,
        "period_end": end,
        "reviewed": sorted(entries),
        "outcomes": [
            {
                "entry": entry_id,
                "verdict": TRIAGE_DRAFT_TEMPLATE_VERDICT,
                "proposal": "",
                "merged_into": "",
                "reason": "",
            }
            for entry_id in sorted(entries)
        ],
        "summary": {"notes": ""},
    }
    directory = paths_module.draft_dir(root, create=True)
    target = paths_module.resolve_within_repo(directory / f"TRG-{args.week}.toml", root)
    paths_module.write_text_atomic(target, canonical_text(TRIAGE_SPEC, data))
    print(f"OK: {target.relative_to(Path(root).resolve()).as_posix()}")
    print(f"棚卸し対象 {len(entries)} 件。verdict と reason を埋めて triage-close で確定する。")
    return EXIT_OK


def cmd_triage_close(args) -> int:
    root = args.root
    data, findings = _load_and_validate(root, TRIAGE_SPEC, args.source)
    if data is None or _errors(findings):
        return _fail(findings)
    return _commit(root, TRIAGE_SPEC, data)


def cmd_check(args) -> int:
    findings = run_checks(
        args.root,
        canonical=args.canonical,
        base_ref=args.base_ref,
        require_base=args.require_base,
    )
    _print(findings)
    errors = _errors(findings)
    warnings = [finding for finding in findings if finding.level == WARN]
    print(f"errors={len(errors)} warnings={len(warnings)}")
    return EXIT_ERROR if errors else EXIT_OK


def cmd_status(args) -> int:
    store = load_store(args.root)
    now = args.now or datetime.date.today()
    states = status_module.compute(store, now)
    if args.entry:
        states = [item for item in states if item.entry_id == args.entry]
        if not states:
            print(f"ERROR: 台帳エントリが見つからない: {args.entry}", file=sys.stderr)
            return EXIT_NOT_FOUND
    summary = status_module.summarize(states)
    if args.json:
        print(json.dumps(
            {"now": now.isoformat(),
             "summary": summary,
             "entries": [item.as_dict() for item in states]},
            ensure_ascii=False, sort_keys=True, indent=2,
        ))
        return EXIT_OK
    for item in states:
        mark = "STALE" if item.stale else "     "
        print(f"{mark} {item.entry_id}  {item.state}  since={item.since} "
              f"age={item.age_days}d  {item.detail}")
    print(f"total={summary['total']} stale={summary['stale']}")
    return EXIT_OK


def cmd_index(args) -> int:
    store = load_store(args.root)
    payload = {
        kind: [document.document_id for document in store.of(kind)]
        for kind in SPECS
    }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2))
    else:
        for kind in sorted(payload):
            print(f"## {kind} ({len(payload[kind])})")
            for document_id in payload[kind]:
                print(f"  {document_id}")
    if not any(payload.values()):
        return EXIT_NOT_FOUND
    return EXIT_OK


# --- parser -----------------------------------------------------------------


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

    new_entry = sub.add_parser("new-entry", help="台帳エントリを新規作成する")
    new_entry.add_argument("--from", dest="source", required=True, help="下書き TOML")
    new_entry.set_defaults(func=cmd_new_entry)

    propose = sub.add_parser("propose", help="改訂案を新規作成する")
    propose.add_argument("--from", dest="source", required=True, help="下書き TOML")
    propose.add_argument("--supersede", default="", help="置き換える既存の改訂案 id")
    propose.set_defaults(func=cmd_propose)

    amend = sub.add_parser("amend-proposal", help="pending の改訂案の本文を差し替える")
    amend.add_argument("--from", dest="source", required=True, help="下書き TOML")
    amend.set_defaults(func=cmd_amend_proposal)

    approve = sub.add_parser("approve", help="改訂案を承認する")
    approve.add_argument("--proposal", required=True)
    approve.add_argument("--triage", required=True, help="承認した棚卸し記録 id")
    approve.add_argument("--by", required=True, help="承認者")
    approve.add_argument("--reason", default="")
    approve.add_argument("--now", type=_parse_date, default=None)
    approve.set_defaults(func=cmd_approve)

    reject = sub.add_parser("reject", help="改訂案を却下する")
    reject.add_argument("--proposal", required=True)
    reject.add_argument("--by", required=True, help="判断者")
    reject.add_argument("--reason", required=True, help="却下理由")
    reject.add_argument("--triage", default="")
    reject.add_argument("--now", type=_parse_date, default=None)
    reject.set_defaults(func=cmd_reject)

    applied = sub.add_parser("apply-done", help="承認済みの改訂案を反映済みにする")
    applied.add_argument("--proposal", required=True)
    applied.add_argument("--issue-ref", required=True, dest="issue_ref")
    applied.add_argument("--applied-pr", required=True, type=int, dest="applied_pr")
    applied.set_defaults(func=cmd_apply_done)

    triage_open = sub.add_parser("triage-open", help="棚卸しの下書きを生成する")
    triage_open.add_argument("--week", required=True, help="YYYY-Wnn")
    triage_open.add_argument("--now", type=_parse_date, default=None)
    triage_open.set_defaults(func=cmd_triage_open)

    triage_close = sub.add_parser("triage-close", help="棚卸し記録を確定する")
    triage_close.add_argument("--from", dest="source", required=True, help="下書き TOML")
    triage_close.set_defaults(func=cmd_triage_close)

    check = sub.add_parser("check", help="機械 lint")
    check.add_argument("--canonical", action="store_true", help="L7（canonical バイト比較）も行う")
    check.add_argument("--base-ref", default=None, dest="base_ref",
                       help="immutability/状態遷移の比較対象（既定: origin/main → main）")
    check.add_argument(
        "--require-base", action="store_true", dest="require_base",
        help=(
            "比較対象（merge base）を解決できないことを ERROR にする。"
            "base を解決できる前提の実行環境（fetch-depth: 0 の CI）で指定し、"
            "L6/P1 が無言で skip されたまま緑になるのを防ぐ"
        ),
    )
    check.set_defaults(func=cmd_check)

    status = sub.add_parser("status", help="導出状態と滞留")
    status.add_argument("--now", type=_parse_date, default=None,
                        help="滞留判定の基準日（テスト・再現用の注入点）")
    status.add_argument("--json", action="store_true")
    status.add_argument("--entry", default="")
    status.set_defaults(func=cmd_status)

    index = sub.add_parser("index", help="文書の一覧")
    index.add_argument("--json", action="store_true")
    index.set_defaults(func=cmd_index)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.root = Path(args.root).resolve() if args.root else paths_module.repo_root()
    try:
        return args.func(args)
    except FeedbackMissing as exc:
        print(f"NOT_FOUND: {exc}", file=sys.stderr)
        return EXIT_NOT_FOUND
    except (FeedbackPathError, DocumentError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return EXIT_ERROR


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
