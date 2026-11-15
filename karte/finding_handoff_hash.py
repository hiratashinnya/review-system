"""申し送り対象の決定論的なハッシュ。"""

import hashlib
import json


def normalize_text(text: str) -> str:
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    return "\n".join(line.rstrip() for line in lines).strip()


def _single_line(value: str) -> str:
    value = normalize_text(value)
    if "\n" in value or "\x00" in value:
        raise ValueError("handoff の項目に改行または NUL は使えません")
    return value


def content_hash(id: str, harm: str, summary: str, locus, expected: str) -> str:
    values = [_single_line(id), _single_line(harm), _single_line(summary),
              sorted(_single_line(item) for item in locus), _single_line(expected)]
    encoded = json.dumps(values, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()
