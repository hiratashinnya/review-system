"""CLI 入力・ブロック値に共通の単項目バリデータ（slug・targets・finding_ids・change_kind）。"""

from .finding_id import parse_finding_id
from .format_error import KarteFormatError
from .value_codec import check_list, check_scalar
from .vocabulary import CHANGE_KINDS, SLUG_RE


def validate_slug(value: str, what: str) -> str:
    text = check_scalar(value, what)
    if not SLUG_RE.match(text):
        raise KarteFormatError(
            f"{what} は slug（英小文字・数字で始まり、以降 a-z 0-9 . _ - のみ）: {value!r}"
        )
    return text


def validate_targets(values) -> list:
    targets = check_list(values, "targets")
    if not targets:
        raise KarteFormatError(
            "targets は 1 つ以上必要（触った関数/クラス単位・例 review_system/forms.py::build_attrs）"
        )
    return targets


def validate_finding_ids(values) -> list:
    ids = check_list(values, "finding_ids")
    if not ids:
        raise KarteFormatError("finding_ids は 1 つ以上必要（指摘↔診断↔処置結果を ID で結合する）")
    for item in ids:
        parse_finding_id(item)
    return ids


def validate_change_kind(value: str) -> str:
    text = check_scalar(value, "change_kind")
    if text not in CHANGE_KINDS:
        raise KarteFormatError(f"change_kind は {list(CHANGE_KINDS)} のいずれか: {value!r}")
    return text
