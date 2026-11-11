"""ブロックのフィールド取得と検証（必須／任意・列挙・整数リスト）。"""

from .block_parser import Block
from .format_error import KarteFormatError
from .int_args import require_ascii_int
from .value_codec import check_scalar


def require(block: Block, key: str):
    if key not in block.fields:
        raise KarteFormatError(
            f"{block.lineno} 行目 '{block.title}': 必須キー '{key}' が無い"
        )
    return block.fields[key]


def require_nonempty(block: Block, key: str) -> str:
    value = require(block, key)
    if isinstance(value, list) or not str(value).strip():
        raise KarteFormatError(
            f"{block.lineno} 行目 '{block.title}': '{key}' が空（必須項目）"
        )
    return str(value).strip()


def require_enum(block: Block, key: str, allowed) -> str:
    value = require_nonempty(block, key)
    if value not in allowed:
        raise KarteFormatError(
            f"{block.lineno} 行目 '{block.title}': '{key}' は {list(allowed)} のいずれか: {value!r}"
        )
    return value


def require_int_list(block: Block, key: str) -> list:
    value = block.fields.get(key, [])
    if isinstance(value, str):
        value = [value] if value.strip() else []
    numbers = []
    for item in value:
        message = f"{block.lineno} 行目 '{block.title}': '{key}' は整数のリスト: {item!r}"
        numbers.append(require_ascii_int(str(item).strip(), KarteFormatError(message)))
    return numbers


def optional_enum(block: Block, key: str, allowed, default: str) -> str:
    """任意キーを列挙で検証する（未記載・空は ``default``・綴り違いは fail-close）。"""
    raw = block.fields.get(key, "")
    if isinstance(raw, list):
        raise KarteFormatError(
            f"{block.lineno} 行目 '{block.title}': '{key}' はリストではなく単一の値で書く"
        )
    text = str(raw).strip()
    if not text:
        return default
    if text not in allowed:
        raise KarteFormatError(
            f"{block.lineno} 行目 '{block.title}': '{key}' は {list(allowed)} のいずれか: {text!r}"
        )
    return text


def optional_scalar(block: Block, key: str) -> str:
    raw = block.fields.get(key, "")
    if isinstance(raw, list):
        raise KarteFormatError(
            f"{block.lineno} 行目 '{block.title}': '{key}' はリストではなく単一の値で書く"
        )
    return check_scalar(raw, key)
