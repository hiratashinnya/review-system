"""レビューア本人の取り込み（``ingest-reviewer``）と、本パッケージ外から足す verb の登録。

``ingest-reviewer`` は Issue を進行ポインタから決め、明示 round は台帳の最新値と同じ場合だけ受け付ける。
通常は ``--round`` を省略してポインタの次 round を使う。ポインタ書込み失敗時は再取り込みせず主文脈へ報告し、
主文脈が ``karte render --issue <N>`` で当該 round の記録を確認してから ``activate`` で向け直す。
詳細は ``karte/README.md``「進行ポインタの書込みが台帳より後に失敗した窓」。``--from`` は
``tmp/_handoff/pr-reviewer--*.md`` に限る（Issue #375）。主文脈専用の ``activate`` / ``decide`` は
:mod:`karte.owner_cli`。
"""

from . import handoff_header, handoff_path, ingest_review, paths, pointer_completion, review_expectation
from .reviewer_policy import ReviewerIngestPolicy
from .verb_boundary import fail_close

@fail_close(locked=True)
def cmd_ingest_reviewer(args, repo_root) -> int:
    issue, round_no = pointer_completion.ingest_target(args, repo_root, pointer_minimum=0)
    expected = review_expectation.require(repo_root, issue)  # 主文脈が記録した期待値（handoff の自己申告ではない）
    report = paths.read_text(handoff_path.resolve_reviewer_handoff(args.source, repo_root))
    handoff_header.check_header(report, issue, round_no, expected)
    policy = ReviewerIngestPolicy(repo_root, issue, round_no)
    return ingest_review.ingest_locked(
        repo_root, issue, round_no, report, policy, allow_same_round=args.round is not None
    )


def register(subparsers, add_issue) -> None:
    ingest = subparsers.add_parser(
        "ingest-reviewer", help="レビューアの handoff を取り込む（--issue 不可）"
    )
    ingest.add_argument("--from", dest="source", required=True,
                        help="tmp/_handoff/pr-reviewer--<key>.md")
    ingest.add_argument(
        "--round",
        help="通常は省略（ポインタの次 round を使う）、明示は台帳最新 round と同じ値に限る。"
             "ポインタ書込み失敗の回復には使わない（karte/README.md 参照）",
    )
    ingest.set_defaults(func=cmd_ingest_reviewer, issue=None, round=None)
