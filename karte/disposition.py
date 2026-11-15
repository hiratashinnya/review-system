"""``disposition``（``harm: real`` の指摘へのオーナー判断の記録）の型と読取り。

設計理由・既知の限界は ``.ai/rationale/karte-module-split.md``「karte/disposition.py」を参照。
"""

from dataclasses import dataclass

from .block_fields import optional_enum, optional_scalar
from .block_parser import Block
from .format_error import KarteFormatError
from .vocabulary import DEFERRED_TO_RE, DISPOSITIONS

DISPOSITION_REQUIRED_KEYS = {
    "fix-here": (),
    "deferred": ("deferred_to",),
    "waived": ("waived_by", "waived_reason"),
}
DISPOSITION_ALL_KEYS = ("deferred_to", "waived_by", "waived_reason")


@dataclass
class Disposition:
    """オーナー判断の記録（Issue #495）。``kind`` が空文字＝未決定。"""

    kind: str = ""
    deferred_to: str = ""
    waived_by: str = ""
    waived_reason: str = ""


def parse_disposition(block: Block) -> Disposition:
    """``disposition`` とその付随キーを読む（未記載は未決定・不整合は fail-close）。

    * ``deferred`` は ``deferred_to``、``waived`` は ``waived_by``/``waived_reason`` が必須。
    * 宣言した ``disposition`` に属さない付随キーは空でなければならない（取り違え防止）。
    * 強制するのは**記録**であって、書いた主体がオーナー本人かは検証しない。
    """
    kind = optional_enum(block, "disposition", DISPOSITIONS, "")
    values = {key: optional_scalar(block, key) for key in DISPOSITION_ALL_KEYS}
    where = f"{block.lineno} 行目 '{block.title}'"

    if not kind:
        present = [key for key, value in values.items() if value]
        if present:
            raise KarteFormatError(
                f"{where}: 'disposition' が無いのに {', '.join(present)} が書かれている"
                f"（先に disposition を {list(DISPOSITIONS)} から決める）"
            )
        return Disposition()

    missing = [key for key in DISPOSITION_REQUIRED_KEYS[kind] if not values[key]]
    if missing:
        raise KarteFormatError(
            f"{where}: 'disposition: {kind}' には {', '.join(missing)} が必須"
            "（deferred は行き先 Issue、waived は誰がどの理由で許可したかを残す）"
        )
    extra = [
        key
        for key in DISPOSITION_ALL_KEYS
        if values[key] and key not in DISPOSITION_REQUIRED_KEYS[kind]
    ]
    if extra:
        raise KarteFormatError(
            f"{where}: 'disposition: {kind}' では {', '.join(extra)} を書けない"
            "（別の処置方針の付随キーが残っていると現行の方針を誤読する）"
        )
    if kind == "deferred" and not DEFERRED_TO_RE.match(values["deferred_to"]):
        raise KarteFormatError(
            f"{where}: 'deferred_to' は Issue 番号（`#123` / `123`）か Issue の URL で書く: "
            f"{values['deferred_to']!r}（散文の申し送りは行き先を解決できない）"
        )
    return Disposition(
        kind=kind,
        deferred_to=values["deferred_to"],
        waived_by=values["waived_by"],
        waived_reason=values["waived_reason"],
    )
