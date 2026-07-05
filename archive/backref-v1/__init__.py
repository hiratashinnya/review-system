"""backref — FND バックリファレンス（辺逆転）の決定的自動化ツール。

FND を resolved にするときの「辺逆転」（forward 辺削除＋処置対象への ``→FND-x`` backward 辺
付与＋DD-3 本文凍結＋z バンプ）を手作業でなく機械的に行う。``reconciliation`` が正本へ書き込む
前に ``python -m backref reverse <FND-id> --apply`` で実行することを想定した write ツール。

パース（ノード発見・file:line・edges）は read-only の ``docidx`` を再利用し、本パッケージは
**書込責務のみ**を担う（docidx の単一責務を侵さない）。標準ライブラリのみ。
"""

from .errors import BackrefError

__all__ = ["BackrefError"]
