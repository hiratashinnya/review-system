"""カルテの取り込み済みラウンドを参照する。"""


def last_round(karte) -> int:
    return max(
        max((r for item in karte.findings for r in item.rounds), default=0),
        max((record.number for record in karte.review_rounds), default=0),
    )
