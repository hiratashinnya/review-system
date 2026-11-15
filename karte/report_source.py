"""report_source の責務。詳細は .ai/rationale/karte-module-split.md。"""
import sys
from . import paths
from .errors import KarteUsageError
from .utf8_text import read_stream_text

STDIN_SOURCE = "-"


def read_report(args, repo_root) -> str:
    """レビューレポートをファイルまたは標準入力から読む。"""
    source = getattr(args, "source", None)
    if source is None:
        raise KarteUsageError("--from が未指定（レポートのパスか `-`（標準入力）を指定する）")
    if str(source) != STDIN_SOURCE:
        return paths.read_text(paths.resolve_within_repo(source, repo_root))
    if sys.stdin is None:
        raise KarteUsageError("`--from -` が指定されたが標準入力が無い")
    text = read_stream_text(sys.stdin)
    if not text.strip():
        raise KarteUsageError(
            "`--from -` の標準入力が空（レビューレポート本文が渡されていない）。"
            "空入力を『指摘なし』とは解釈しない"
        )
    return text
