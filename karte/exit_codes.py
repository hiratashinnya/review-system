"""karte verb の終了コード（``dsv2`` に合わせる）。"""

EXIT_OK = 0
EXIT_NOT_FOUND = 2
EXIT_SATURATED = 3
EXIT_ERROR = 4
# 台帳へ取り込み済み（書き込み・引き継ぎ済み）だが、レビューア出力に再掲漏れがあり完了扱いにしない（Issue #375）
EXIT_INCOMPLETE = 5
