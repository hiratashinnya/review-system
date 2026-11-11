"""承認済み Issue と進行ポインタから reviewer の取込先を固定する。"""

from pathlib import Path

from karte import active_pointer, karte_loader, karte_rounds, paths
from karte.errors import KarteNotFound, KarteUsageError
from karte.int_args import parse_int, require_ascii_int

from .errors import CodexExecError


def progress_target(root: Path) -> tuple[int, int]:
    active = active_pointer.read_active(root, required=True)
    if "issue" not in active or "round" not in active:
        raise KarteUsageError("進行ポインタに issue または round が無い")
    issue = paths.validate_issue(active["issue"])
    current = parse_int(active["round"], "round", minimum=0)
    try:
        latest = karte_rounds.last_round(karte_loader.load_karte(root, issue)[1])
    except KarteNotFound:
        latest = 0
    if current != latest:
        raise KarteUsageError(
            f"進行ポインタ round={current} と issue-{issue} の最新 round={latest} が不一致"
        )
    next_round = require_ascii_int(current + 1, KarteUsageError("次の round が上限を超える"))
    return issue, next_round


def capture_target(root: Path, expected_issue: int | None) -> tuple[int, int, int]:
    try:
        if expected_issue is None:
            raise KarteUsageError("承認済み binding から expected.issue を取得できない")
        issue, next_round = progress_target(root)
        if issue != expected_issue:
            raise KarteUsageError(
                f"進行ポインタ issue-{issue} と承認済み expected.issue={expected_issue} が不一致"
            )
        return issue, next_round - 1, next_round
    except Exception as error:
        raise CodexExecError("CODEX_REVIEW_INGEST_FAILED", str(error)) from None
