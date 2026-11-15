"""``## Section`` / ``### Title`` ＋ ``key: value`` 行の決定論ブロックパーサ。"""

from dataclasses import dataclass

from .format_error import KarteFormatError
from .value_codec import parse_value
from .vocabulary import KEY_RE


@dataclass
class Block:
    section: str | None
    title: str
    fields: dict
    lineno: int


def parse_blocks(text: str, *, allow_preamble: bool = False) -> list:
    """``## Section`` / ``### Title`` ＋ ``key: value`` 行の決定論パーサ。

    解釈できない行が 1 行でもあれば :class:`KarteFormatError`（fail-close）。

    ``allow_preamble``
        最初の ``### `` 見出しより**前**の自由記述行を読み飛ばす（レビューレポート専用の緩和）。
        1 件目のブロックに入った後は緩和しない。``key: value`` 形の行は preamble でも拒否する。
    """
    blocks: list = []
    section = None
    current = None
    seen_block = False
    for lineno, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("<!--"):
            continue
        if line.startswith("### "):
            current = Block(section, line[4:].strip(), {}, lineno)
            blocks.append(current)
            seen_block = True
            continue
        if line.startswith("## "):
            section = line[3:].strip()
            current = None
            continue
        if line.startswith("# "):
            current = None
            continue
        matched = KEY_RE.match(line)
        if matched and current is not None:
            key = matched.group(1)
            if key in current.fields:
                raise KarteFormatError(f"{lineno} 行目: キー '{key}' が重複している")
            current.fields[key] = parse_value(matched.group(2))
            continue
        if allow_preamble and not seen_block and not matched:
            continue
        raise KarteFormatError(f"{lineno} 行目: 解釈できない行: {line!r}")
    return blocks
