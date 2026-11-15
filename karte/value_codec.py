"""カルテの 1 行値（スカラ／``[a, b]`` リスト）の読み書きと文字検査。

``locus`` 正規化の設計理由は ``.ai/rationale/karte-module-split.md``「karte/value_codec.py」を参照。
"""

from .format_error import KarteFormatError
from .vocabulary import FORBIDDEN_LIST_ITEM_CHARS, FORBIDDEN_VALUE_CHARS


def parse_value(raw: str):
    """``[a, b]`` はリスト、それ以外はスカラ文字列として解釈する。"""
    text = raw.strip()
    if text.startswith("[") and text.endswith("]"):
        inner = text[1:-1].strip()
        if not inner:
            return []
        return [part.strip() for part in inner.split(",") if part.strip()]
    return text


def format_value(value) -> str:
    if value is None:
        return ""
    if isinstance(value, (list, tuple)):
        return "[" + ", ".join(str(item) for item in value) + "]"
    return str(value)


def check_scalar(value, what: str) -> str:
    text = "" if value is None else str(value)
    for bad in FORBIDDEN_VALUE_CHARS:
        if bad in text:
            raise KarteFormatError(f"{what} に改行/NUL は書けない: {text!r}")
    return text.strip()


def check_list(values, what: str) -> list:
    if isinstance(values, str):
        raise KarteFormatError(f"{what} はリスト（`[a, b]`）で書く: {values!r}")
    checked = []
    for item in values:
        text = check_scalar(item, what)
        if not text:
            continue
        for bad in FORBIDDEN_LIST_ITEM_CHARS:
            if bad in text:
                raise KarteFormatError(f"{what} の要素に {bad!r} は使えない: {text!r}")
        if text not in checked:
            checked.append(text)
    return checked


def normalize_locus(value) -> list:
    """``locus`` をリストへ正規化する（スカラ 1 件でもリストでも受ける・空は空リスト）。

    スカラ経路もリスト要素と同じ文字検査を通す（読み戻しで要素が割れて再発番を見逃さないため）。
    """
    if isinstance(value, (list, tuple)):
        return check_list(value, "locus")
    text = check_scalar(value, "locus")
    return check_list([text], "locus") if text else []
