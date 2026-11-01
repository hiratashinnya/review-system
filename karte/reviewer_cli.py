"""レビューア本人の取り込み（``ingest-reviewer``）と、本パッケージ外から足す verb の登録。

``ingest-reviewer`` は Issue/round を進行ポインタからしか決められず、``--from`` は
``tmp/_handoff/pr-reviewer--*.md`` に限る（Issue #375）。主文脈専用の ``activate`` / ``decide`` は
:mod:`karte.owner_cli`。
"""

from . import handoff_header, handoff_path, ingest_review, model, owner_cli, paths
from .exit_codes import EXIT_OK
from .pointer_round import next_round
from .reviewer_policy import ReviewerIngestPolicy
from .verb_support import fail_close, repo_root_of, resolve_issue

cmd_activate = owner_cli.cmd_activate  # 呼び出し側（テスト）が従来の名前で参照できるようにする
cmd_decide = owner_cli.cmd_decide


@fail_close
def cmd_ingest_reviewer(args) -> int:
    repo_root = repo_root_of(args)
    issue = resolve_issue(args, repo_root)
    report = paths.read_text(handoff_path.resolve_reviewer_handoff(args.source, repo_root))
    with paths.writer_lock(repo_root):
        round_no = next_round(repo_root, issue)
        handoff_header.check_header(report, issue, round_no)
        policy = ReviewerIngestPolicy(repo_root, issue, round_no)
        code = ingest_review.ingest_locked(repo_root, issue, round_no, report, policy)
    if code == EXIT_OK and policy.kept_owner_scope:
        kept = ", ".join(policy.kept_owner_scope)
        print(f"  オーナーが確定した scope を保持（レビューア申告と台帳が不一致）: {kept}")
    return code


def register(subparsers, add_issue) -> None:
    ingest = subparsers.add_parser(
        "ingest-reviewer", help="レビューア本人が handoff のレポートを取り込む（--issue/--round 不可）"
    )
    ingest.add_argument("--from", dest="source", required=True,
                        help="tmp/_handoff/pr-reviewer--<key>.md")
    ingest.set_defaults(func=cmd_ingest_reviewer, issue=None, round=None)

    activate = subparsers.add_parser("activate", help="進行ポインタを Issue に向ける（主文脈専用）")
    activate.add_argument("--issue", required=True, help="Issue 番号")
    activate.add_argument(
        "--repair-declared-scope", action="store_true",
        help="壊れた申告 scope の原本の行を除いて復旧する（元は .bak* に世代を分けて残す）",
    )
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
