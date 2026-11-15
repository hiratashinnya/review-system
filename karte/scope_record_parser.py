"""申告 scope の JSONL 検証。"""

import json

from .model import KarteFormatError

OWNER = "owner"
SCOPES = ("in", "out")
REPAIR_HINT = "（主文脈が `python3 -m karte activate --issue {issue} --repair-declared-scope` で復旧する）"


def record_of(line):
    """壊れたレコードは ValueError に正規化する。"""
    try:
        record = json.loads(line)
        round_no, finding_id, scope = record["round"], record["id"], record["scope"]
        by = record.get("by", "")
    except (ValueError, KeyError, TypeError, AttributeError, RecursionError) as exc:
        raise ValueError(repr(exc)) from None
    if isinstance(round_no, bool) or not isinstance(round_no, int):
        raise ValueError("round は整数でなければならない")
    if not isinstance(finding_id, str) or scope not in SCOPES or by not in ("", OWNER):
        raise ValueError("id は文字列、scope は in/out、by は省略か owner でなければならない")
    return round_no, finding_id, scope, by


def records_of(path, issue, text):
    records = []
    for number, line in enumerate((text or "").splitlines(), start=1):
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
