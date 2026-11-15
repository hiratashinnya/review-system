"""Issue #801: owner-only AC checkbox 更新を本文の差分検証付きで計画する。

このモジュールはGitHub APIを呼ばない。主文脈は live Issue 本文を再取得し、
この関数が返した本文だけを更新し、再取得で完全一致を検査する。
"""

from .ac_snapshot import CHECKBOX, digest, from_issue_body
from .errors import KarteUsageError


def plan(snapshot_body: str, live_body: str, judgments) -> tuple[str, list[int]]:
    """snapshotとの競合をfail-close。satisfiedの未チェックcheckboxのみ変更する。"""
    frozen = from_issue_body(snapshot_body)
    live = from_issue_body(live_body)
    if digest(frozen) != digest(live):
        raise KarteUsageError("レビュー開始時のACとlive本文が異なるためチェック更新を中止")
    by_number = {}
    for item in judgments:
        number, result = item.number, item.result
        if type(number) is not int or number < 1 or number > len(frozen) or number in by_number:
            raise KarteUsageError("レビュー結果のAC番号が不正または重複")
        if result not in ("satisfied", "not_met", "unverified"):
            raise KarteUsageError("AC判定が不正")
        by_number[number] = result
    if set(by_number) != set(range(1, len(frozen) + 1)):
        raise KarteUsageError("レビュー結果にAC全件が含まれていない")
    lines = live_body.splitlines(keepends=True)
    changed = []
    for number, (ac, latest) in enumerate(zip(frozen, live), start=1):
        result = by_number[number]
        if result != "satisfied":
            if ac.checked is True:
                raise KarteUsageError(f"チェック済みAC{number}が未充足/未検証。オーナー判断まで停止")
            continue
        if latest.checked is None or latest.checked is True:
            continue
        i = latest.line_number - 1
        line = lines[i]
        matched = CHECKBOX.match(line)
        if not matched:
            raise KarteUsageError(f"AC{number}のチェック位置が不正")
        lines[i] = matched.group(1) + "[x]" + matched.group(3) + line[len(matched.group(0)):]
        changed.append(number)
    new_body = "".join(lines)
    if from_issue_body(new_body) != tuple(
        type(ac)(ac.text, True if i + 1 in changed else ac.checked, ac.line_number)
        for i, ac in enumerate(live)
    ):
        raise KarteUsageError("チェック更新後のAC構造が予期せず変化")
    return new_body, changed


def verify_written(expected_body: str, readback_body: str) -> None:
    """GitHub再取得で本文全体の一致を確認。TOCTOU完全排除は保証しない。"""
    if expected_body != readback_body:
        raise KarteUsageError("GitHub Issue本文のread-backが更新予定本文と一致しない")
