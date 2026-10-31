"""karte verb が投げる前提違反の例外（fail-close の境界は ``karte.cli._fail_close``）。"""


class KarteUsageError(Exception):
    """前提違反（存在しない Attempt・未知 finding ID 等）。fail-close で何も書かない。"""


class KarteNotFound(KarteUsageError):
    """対象のカルテがまだ存在しない（未検出＝EXIT_NOT_FOUND）。"""
