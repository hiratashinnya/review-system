"""review handoff の期待値（共通 envelope）を進行ポインタに置く（Issue #375）。

期待値を決めるのは主文脈（``activate`` の引数）か trusted wrapper の承認済み binding で、reviewer の
handoff は自己申告するだけ。``ingest-reviewer`` が申告を期待値へ完全に束縛する。期待値は 1 回限りで、
取り込みが成功すると進行ポインタの書き換えで消える（再利用された handoff は期待値が無く拒否される）。
期待値が残っている間は、その Issue の review は ``ingest-reviewer`` で取り込む前提なので、他 Issue 宛も
主文脈の ``ingest-review`` を拒否する（round 1 を含め、期待値とレビューアの申告原本を守る）。
"""

from . import paths, review_envelope
from .active_pointer import read_active
from .errors import KarteUsageError

EXPECT_KEY = "review_expect"
ENVELOPE_ARGS = ("run_id", "target_key", "snapshot_oid", "input_digest", "phase")


def from_args(args, issue: int):
    """``activate`` の引数から期待値を作る。1 つも無ければ None、一部だけなら拒否する。"""
    given = {key: getattr(args, key, None) for key in ENVELOPE_ARGS}
    if not any(value is not None for value in given.values()):
        return None
    absent = [key for key, value in given.items() if value is None]
    if absent:
        raise KarteUsageError(
            "review envelope の期待値は全項目を同時に指定する"
            f"（不足: {', '.join('--' + key.replace('_', '-') for key in absent)}）"
        )
    try:
        return review_envelope.expected_of(issue=issue, **given)
    except ValueError as exc:
        raise KarteUsageError(f"review envelope の期待値が不正: {exc}") from None


def pending(repo_root, issue: int):
    """``issue`` について進行ポインタが持つ期待値。無ければ（他 Issue 向けを含む）None、壊れた値は拒否する。"""
    active = read_active(repo_root)
    if EXPECT_KEY not in active or "issue" not in active or paths.validate_issue(active["issue"]) != issue:
        return None
    expected = active[EXPECT_KEY]
    if not isinstance(expected, dict) or set(expected) != set(review_envelope.BOUND):
        raise KarteUsageError("進行ポインタの review 期待値が壊れている（activate をやり直す）")
    if expected["issue"] != issue:
        raise KarteUsageError("進行ポインタの review 期待値が対象 Issue と食い違う（activate をやり直す）")
    return expected


def require(repo_root, issue: int) -> dict:
    expected = pending(repo_root, issue)
    if expected is None:
        raise KarteUsageError(
            "進行ポインタに review envelope の期待値が無い。主文脈が `karte activate --issue <N> "
            "--run-id .. --target-key .. --snapshot-oid .. --input-digest .. --phase ..` を実行する"
            "（取り込み済みの handoff の再利用も同じ理由で拒否される）"
        )
    return expected


def refuse_main_context_ingest(repo_root, issue: int) -> None:
    """期待値が残っている間は、主文脈の ``ingest-review`` で review を取り込ませない。"""
    active = read_active(repo_root)
    if EXPECT_KEY not in active:
        return
    waiting_issue = paths.validate_issue(active.get("issue"))
    if pending(repo_root, waiting_issue) is not None:
        raise KarteUsageError(
            f"Issue {waiting_issue} はレビューア本人の取り込み待ち（進行ポインタに review envelope の期待値がある）。"
            f"主文脈の ingest-review は他 Issue 宛も使えない。Issue {waiting_issue} の `ingest-reviewer` を待つか、"
            f"取り込まない場合は `karte activate --issue {waiting_issue}`（期待値なし）で待ちを解除する"
        )
