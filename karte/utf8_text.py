"""テキストの入出力境界で UTF-8 として正しいものだけを通す。

不正バイトは読み側で ``UnicodeDecodeError``、argv などに混じる lone surrogate は書き側で
``UnicodeEncodeError``（どちらも ``ValueError`` 系）になり、終了コード契約 {0,2,3,4} の外へ漏れる。
"""

from .errors import KarteUsageError


def read_stream_text(stream) -> str:
    """``stream`` を全部読む。UTF-8 として正しくなければ :class:`KarteUsageError`。

    C ロケールでは stdin が ``surrogateescape`` で読まれ、不正バイトが lone surrogate として通るので、
    UTF-8 へ戻せることも確かめる（台帳への書込みで初めて失敗するのを防ぐ）。
    """
    try:
        text = stream.read()
        text.encode("utf-8")
    except UnicodeError:
        raise KarteUsageError("標準入力が UTF-8 として読めない（不正なバイト列を含む）") from None
    return text


def require_utf8_encodable(text: str, what) -> None:
    """``text`` を UTF-8 で書けなければ :class:`KarteUsageError`（書込みの前に呼ぶ）。"""
    try:
        text.encode("utf-8")
    except UnicodeEncodeError:
        raise KarteUsageError(f"{what} に UTF-8 で書けない文字（不正なバイト列由来）を含む") from None
