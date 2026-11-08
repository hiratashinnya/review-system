"""カルテの取り込み済みラウンドを参照する。"""


def last_round(karte) -> int:
    return max((r for item in karte.findings for r in item.rounds), default=0)
