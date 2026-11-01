"""申告 scope の原本ファイル（``tmp/_karte/issue-<N>.declared-scope.jsonl``）の読み書き部品。

1 行 1 レコード：レビューアの申告 ``{"round", "id", "scope"}``、またはオーナーの確定
``{"round", "id", "scope", "by": "owner"}``（``decide --scope`` が足す）。書込みは常に
「既存の全行を検証 → 新しい全体を一時ファイルへ書いて置換」で、途中までの行を作らない。
"""

import json

from . import paths
from .model import KarteFormatError

DECLARED_SCOPE_FMT = "issue-{issue}.declared-scope.jsonl"
OWNER = "owner"
SCOPES = ("in", "out")
REPAIR_HINT = "（主文脈が `python3 -m karte activate --issue {issue} --repair-declared-scope` で復旧する）"


def ledger_path(issue, repo_root, *, create=False):
    return paths.karte_dir(repo_root, create=create) / DECLARED_SCOPE_FMT.format(issue=issue)


def exists(issue, repo_root) -> bool:
    """この Issue に原本があるか（置き場が無ければ無い）。"""
    try:
        return ledger_path(issue, repo_root).exists()
    except paths.KarteMissing:
        return False


def record_of(line):
    """1 行を ``(round, id, scope, by)`` にする。``by`` は申告なら ``""``。壊れていれば ``ValueError``。"""
    try:
        record = json.loads(line)
        round_no, finding_id, scope = record["round"], record["id"], record["scope"]
        by = record.get("by", "")
    except (ValueError, KeyError, TypeError, AttributeError) as exc:
        raise ValueError(repr(exc)) from None
    if isinstance(round_no, bool) or not isinstance(round_no, int):
        raise ValueError("round は整数でなければならない")
    if not isinstance(finding_id, str) or scope not in SCOPES or by not in ("", OWNER):
        raise ValueError("id は文字列、scope は in/out、by は省略か owner でなければならない")
    return round_no, finding_id, scope, by


def read_records(issue, repo_root):
    """``[(line, (round, id, scope, by))]``。1 行でも壊れていれば :class:`KarteFormatError`。"""
    try:
        path = ledger_path(issue, repo_root)
    except paths.KarteMissing:  # 置き場ごと無い＝まだ何も取り込んでいない
        return []
    if not path.is_file():
        return []
    records = []
    for number, line in enumerate(paths.read_text(path).splitlines(), start=1):
        if not line.strip():
            continue
        try:
            records.append((line, record_of(line)))
        except ValueError as exc:
            raise KarteFormatError(
                f"申告 scope の原本 {path} の {number} 行目が壊れている（{exc}）。"
                f"台帳との差分を判定できないため拒否する{REPAIR_HINT.format(issue=issue)}"
            ) from None
    return records


def append_lines(issue, repo_root, new_lines) -> None:
    """既存の全行を検証したうえで ``new_lines`` を足し、全体を原子的に置換する。"""
    lines = [line for line, _record in read_records(issue, repo_root)] + list(new_lines)
    paths.write_text_atomic(ledger_path(issue, repo_root, create=True), "\n".join(lines) + "\n")
