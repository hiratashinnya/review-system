"""整数引数（``--round`` / ``--attempt`` / ポインタ値）の fail-close な検証。"""

from .errors import KarteUsageError


def parse_int(value, label: str, minimum: int = 1) -> int:
    """``minimum`` 以上の整数に直す。ASCII 数字だけを受け、それ以外は :class:`KarteUsageError`。

    ``str.isdigit()`` だけでは ``"²"`` のような非 ASCII 数字を通し、``int()`` が ``ValueError`` で
    終了コード契約の外へ漏れる。
    """
    text = str(value)
    try:
        number = int(text) if text.isascii() and text.isdigit() else -1
    except ValueError:  # 桁数が多すぎる（int の変換上限）
        number = -1
    if number < minimum:
        raise KarteUsageError(f"{label} は {minimum} 以上の整数: {text[:40]!r}")
    return number
