"""レビューア本人の取り込み（``ingest-reviewer``）と、主文脈専用の ``activate`` / ``decide``。

``ingest-reviewer`` は Issue/round を進行ポインタからしか決められず、``--from`` は
``tmp/_handoff/pr-reviewer--*.md`` に限る（Issue #375）。
"""

from . import handoff_path, ingest_review, model, owner_decision, paths, scope_ledger
from .active_pointer import write_active
from .errors import KarteNotFound
from .exit_codes import EXIT_OK
from .reviewer_policy import ReviewerIngestPolicy
from .verb_support import fail_close, load_karte, next_round, repo_root_of, resolve_issue


@fail_close
def cmd_ingest_reviewer(args) -> int:
    repo_root = repo_root_of(args)
    issue = resolve_issue(args, repo_root)
    report = paths.read_text(handoff_path.resolve_reviewer_handoff(args.source, repo_root))
    with paths.writer_lock(repo_root):
        round_no = next_round(repo_root, issue)
        policy = ReviewerIngestPolicy(repo_root, issue, round_no)
        code = ingest_review.ingest_locked(repo_root, issue, round_no, report, policy)
        if code == EXIT_OK:
            _, karte = load_karte(repo_root, issue)
            overridden = scope_ledger.overridden(karte, scope_ledger.latest_declared(issue, repo_root))
            if overridden:
                print(f"  オーナーが覆した scope（レビューア申告と台帳が不一致）: {', '.join(overridden)}")
    return code


@fail_close
def cmd_activate(args) -> int:
    """進行ポインタを対象 Issue へ向ける（round は台帳の取り込み済み最新。台帳が無ければ 0）。"""
    repo_root = repo_root_of(args)
    issue = paths.validate_issue(args.issue)
    with paths.writer_lock(repo_root):
        try:
            _, karte = load_karte(repo_root, issue)
            last = max((r for item in karte.findings for r in item.rounds), default=0)
        except KarteNotFound:  # 台帳が無い＝初回
            last = 0
        write_active(repo_root, issue, last)
    print(f"=== activate: issue-{issue} round {last}（次の ingest-reviewer は round {last + 1}）===")
    return EXIT_OK


@fail_close
def cmd_decide(args) -> int:
    repo_root = repo_root_of(args)
    issue = resolve_issue(args, repo_root)
    options = {
        "disposition": args.disposition, "deferred_to": args.deferred_to,
        "waived_by": args.waived_by, "waived_reason": args.waived_reason,
    }
    with paths.writer_lock(repo_root):
        path, karte = load_karte(repo_root, issue)
        lines = owner_decision.record_decision(karte, args.finding, options, args.scope)
        owner_decision.write_karte(path, karte)
    print(f"=== decide: {args.finding} ===")
    print("  " + " / ".join(lines))
    return EXIT_OK


def register(subparsers, add_issue) -> None:
    ingest = subparsers.add_parser(
        "ingest-reviewer", help="レビューア本人が handoff のレポートを取り込む（--issue/--round 不可）"
    )
    ingest.add_argument("--from", dest="source", required=True,
                        help="tmp/_handoff/pr-reviewer--<key>.md")
    ingest.set_defaults(func=cmd_ingest_reviewer, issue=None, round=None)

    activate = subparsers.add_parser("activate", help="進行ポインタを Issue に向ける（主文脈専用）")
    activate.add_argument("--issue", required=True, help="Issue 番号")
    activate.set_defaults(func=cmd_activate)

    decide = subparsers.add_parser("decide", help="オーナー決定を台帳へ記録する（主文脈専用）")
    add_issue(decide)
    decide.add_argument("--finding", required=True, help="対象の finding ID")
    decide.add_argument("--disposition", choices=list(model.DISPOSITIONS))
    decide.add_argument("--deferred-to")
    decide.add_argument("--waived-by")
    decide.add_argument("--waived-reason")
    decide.add_argument("--scope", help="オーナーが覆した scope（in|out）")
    decide.set_defaults(func=cmd_decide)
