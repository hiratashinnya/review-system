"""申し送りの観測・検証に関する使用エラー。"""

from .errors import KarteUsageError


class FindingHandoffError(KarteUsageError):
    """呼び出し元が処置を選べる失敗種別を保持する。"""

    def __init__(self, kind: str, message: str):
        super().__init__(message)
        self.kind = kind
