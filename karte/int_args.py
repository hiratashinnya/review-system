"""整数引数・台帳/ポインタ内の整数の fail-close な変換（非 ASCII 数字・巨大桁を拒否する）。"""

from .errors import KarteUsageError

# 桁数の上限。str()/int() は 4300 桁超で ValueError になるので、`+ 1` した結果を文字列にしても
# 届かない余裕のある値で止める（ID・ラウンド・連番は 64bit に収まれば足りる）。
MAX_DIGITS = 18


def ascii_int_or_none(value) -> int | None:
    """ASCII 数字だけの文字列を int にする。非 ASCII 数字・:data:`MAX_DIGITS` 桁超・数字以外は ``None``。

    ``str.isdigit()`` だけでは ``"²"`` を通し、``int()`` は ``ValueError`` で終了コード契約
    {0,2,3,4} の外（traceback の終了コード 1）へ漏れる。桁数を絞るのは、変換上限ちょうどの値が
    受理されて次の ``+ 1`` で ``str()`` に失敗するのを防ぐため。整数変換はここを唯一の入口にする。
    """
    text = str(value)
    if len(text) > MAX_DIGITS or not (text.isascii() and text.isdigit()):
        return None
    return int(text)


def require_ascii_int(value, error: Exception) -> int:
    """:func:`ascii_int_or_none` が ``None`` なら ``error`` を投げる（拒否例外は呼び出し側の種別を使う）。"""
    number = ascii_int_or_none(value)
    if number is None:
        raise error
    return number


def matched_int(text: str, error_cls: type, what: str) -> int:
    """正規表現で数字列と確認済みの断片を int にする。巨大桁は ``error_cls`` で拒否する。"""
    return require_ascii_int(text, error_cls(f"{what}の桁数が多すぎる: {text[:40]!r}"))


def parse_int(value, label: str, minimum: int = 1) -> int:
    """``minimum`` 以上の整数に直す。ASCII 数字だけを受け、それ以外は :class:`KarteUsageError`。"""
    number = ascii_int_or_none(value)
    if number is None or number < minimum:
        raise KarteUsageError(f"{label} は {minimum} 以上の整数: {str(value)[:40]!r}")
    return number
