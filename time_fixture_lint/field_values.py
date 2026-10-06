"""Extract suspicious absolute-date and epoch fields without changing vocabulary."""
from .patterns import FIELD_TOKEN_RE, SUSPICIOUS_FIELD_RE, ABS_DATE_VALUE_RE, EPOCH_VALUE_RE

def _field_hits_in_line(line: str) -> list[tuple[str, str]]:
    """1行から `key: value` トークンを全て抽出する（1行に複数フィールドがあっても良い）。"""
    hits: list[tuple[str, str]] = []
    for m in FIELD_TOKEN_RE.finditer(line):
        value = m.group(2)
        if value is None:
            value = m.group(3)
        if value is None:
            value = m.group(4) or ""
        hits.append((m.group(1), value.strip()))
    return hits


def _suspicious_fields_in_text(text: str) -> list[tuple[int, str, str]]:
    """(line_no, field_name, value) を疑わしいフィールドの行から抽出する。"""
    hits: list[tuple[int, str, str]] = []
    for line_no, line in enumerate(text.splitlines(), 1):
        for name, value in _field_hits_in_line(line):
            if not SUSPICIOUS_FIELD_RE.search(name):
                continue
            if not (ABS_DATE_VALUE_RE.match(value) or EPOCH_VALUE_RE.match(value)):
                continue
            hits.append((line_no, name, value))
    return hits


def _occurrence_lines(text: str, basenames: set[str]) -> list[int]:
    """fixture basename（フルネーム/stem）が現れる行番号を全て返す。"""
    return [
        line_no
        for line_no, line in enumerate(text.splitlines(), 1)
        if any(b in line for b in basenames)
    ]
