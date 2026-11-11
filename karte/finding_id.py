"""finding ID（``F-<issue>-<seq>``）の書式化と分解。"""

from .format_error import KarteFormatError
from .int_args import matched_int
from .vocabulary import FINDING_ID_RE


def format_finding_id(issue: int, seq: int) -> str:
    """``F-{issue}-{seq}``（seq は 2 桁ゼロ詰め・例 ``F-312-03``）。読み戻せない桁数の番号は書かない。"""
    return f"F-{int(issue)}-{matched_int(str(seq), KarteFormatError, '連番'):02d}"


def parse_finding_id(value: str):
    """``F-<issue>-<seq>`` を ``(issue, seq)`` に分解する。形式違反は例外。"""
    text = str(value).strip()
    matched = FINDING_ID_RE.match(text)
    if not matched:
        raise KarteFormatError(
            f"finding ID の形式違反（期待 `F-<issue>-<seq>`・例 F-312-03）: {value!r}"
        )
    return tuple(matched_int(g, KarteFormatError, "finding ID の番号") for g in matched.groups())
