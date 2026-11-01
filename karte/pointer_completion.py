"""``--issue`` / ``--round`` の補完（進行ポインタ ``tmp/_karte/active.json`` から）。

明示された値の検証は台帳もポインタも読まない。ポインタを読むのは省略されたときだけ。
補完の規約（verb ごとの違い・fail-close の範囲）は :mod:`karte.cli` の docstring。
"""

from . import paths
from .active_pointer import read_active
from .errors import KarteUsageError
from .int_args import parse_int


def resolve_issue(args, repo_root) -> int:
    """``--issue`` が無ければ進行ポインタの ``issue``。ポインタが無い・壊れている・欠けるなら拒否する。"""
    if getattr(args, "issue", None) is not None:
        return paths.validate_issue(args.issue)
    active = read_active(repo_root, required=True)
    if "issue" not in active:
        raise KarteUsageError(
            "--issue が未指定で、進行ポインタ tmp/_karte/active.json に 'issue' が無い"
            "（先に `ingest-review --issue N --round R` を実行する）"
        )
    return paths.validate_issue(active["issue"])


def pointer_round(args, repo_root, issue: int, no_round_hint: str) -> int:
    """``--round`` を検証して返す。省略時は進行ポインタの ``round``（最後に取り込んだラウンド）。

    ポインタが無い・壊れている・``round`` を欠く・``issue`` が対象と食い違う場合は推測せず
    fail-close する。``no_round_hint`` は ``round`` を欠くときの案内。
    """
    if getattr(args, "round", None) is not None:
        return parse_int(args.round, "round")
    active = read_active(repo_root, required=True)
    if "round" not in active:
        raise KarteUsageError(
            "--round が未指定で、進行ポインタ tmp/_karte/active.json に 'round' も無い"
            + no_round_hint
        )
    if "issue" in active and paths.validate_issue(active["issue"]) != issue:
        raise KarteUsageError(
            f"進行ポインタが指す issue-{active['issue']} と対象 issue-{issue} が食い違う"
            "（--round を明示するか、対象 Issue の取り込みからやり直す）"
        )
    return parse_int(active["round"], "round")


def ingest_target(args, repo_root) -> tuple:
    """``ingest-review`` の ``(issue, round)``。順は issue→round。``--round`` 省略時はポインタ**＋1**（K-13）。

    ポインタが持つのは最後に取り込んだラウンドなので、新しいレポートは必ずその次になる
    （同じ番号の再取り込みは単調増加の検査に掛かる）。
    """
    issue = resolve_issue(args, repo_root)
    base = pointer_round(args, repo_root, issue, "（初回の取り込みは `--round 1` を明示する）")
    return issue, (base if getattr(args, "round", None) is not None else base + 1)
