"""カルテ／レビューレポートの書式違反を表す例外（解析・検証モジュール群の共通土台）。"""


class KarteFormatError(Exception):
    """カルテ／レビューレポートの書式違反・スキーマ違反（fail-close）。"""
