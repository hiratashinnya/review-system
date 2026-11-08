"""``--issue`` / ``--round`` の補完（進行ポインタ ``tmp/_karte/active.json`` から）。

明示された値の検証は台帳もポインタも読まない。ポインタを読むのは省略されたときだけ。
補完の規約（verb ごとの違い・fail-close の範囲）は :mod:`karte.cli` の docstring。
"""

from . import paths
from .active_pointer import read_active
from .errors import KarteUsageError
from .int_args import parse_int, require_ascii_int
from .round_resolution import MissingRoundHint, ResolvedRound


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


def resolve_round(args, repo_root, issue: int, missing_hint: MissingRoundHint, *, pointer_minimum=1) -> ResolvedRound:
    """``--round`` を検証して返す。省略時は進行ポインタの ``round``（最後に取り込んだラウンド）。

    戻り値の ``explicit`` で明示か補完かを区別する。ポインタが無い・壊れている・``round`` を欠く・
    ``issue`` が対象と食い違う場合は推測せず fail-close する。``missing_hint`` は ``round`` を
    欠くときに添える案内。
    """
    if getattr(args, "round", None) is not None:
        return ResolvedRound(parse_int(args.round, "round"), explicit=True)
    active = read_active(repo_root, required=True)
    if "round" not in active:
        raise KarteUsageError(
            "--round が未指定で、進行ポインタ tmp/_karte/active.json に 'round' も無い"
            + missing_hint.value
        )
    if "issue" in active and paths.validate_issue(active["issue"]) != issue:
        raise KarteUsageError(
            f"進行ポインタが指す issue-{active['issue']} と対象 issue-{issue} が食い違う"
            "（--round を明示するか、対象 Issue の取り込みからやり直す）"
        )
    return ResolvedRound(parse_int(active["round"], "round", minimum=pointer_minimum), explicit=False)


def recorded_round(active: dict, issue: int) -> int | None:
    """進行ポインタが ``issue`` について記録しているラウンド。縮退してよい場合は ``None``。

    ``None`` になるのは、ポインタの ``issue`` が対象と一致しない（キー欠落・型違いを含む）か、
    ``round`` が偽値（欠落・0・null・空・false）のとき。それ以外の ``round`` は
    :func:`parse_int` で検証し、非 ASCII・巨大桁・負・NaN・bool などは :class:`KarteUsageError`。
    停止ゲートではない verb（``append`` の補完・``render`` の見出し）だけが使う。
    """
    if active.get("issue") != issue or not active.get("round"):
        return None
    return parse_int(active["round"], "round")


def ingest_target(args, repo_root, *, pointer_minimum=1) -> tuple:
    """``ingest-review`` の ``(issue, round)``。順は issue→round。``--round`` 省略時はポインタ**＋1**（K-13）。

    ポインタが持つのは最後に取り込んだラウンドなので、新しいレポートは必ずその次になる
    （同じ番号の再取り込みは単調増加の検査に掛かる）。
    """
    issue = resolve_issue(args, repo_root)
    resolved = resolve_round(args, repo_root, issue, MissingRoundHint.FIRST_INGEST, pointer_minimum=pointer_minimum)
    if resolved.explicit:
        return issue, resolved.number
    return issue, require_ascii_int(
        resolved.number + 1, KarteUsageError("進行ポインタの round に 1 を足すと桁数の上限を超える")
    )
