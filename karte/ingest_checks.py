"""``ingest-review`` のレポート検証（ID 重複・未知 ID・再発番・distinct_from・不在禁止）。

設計理由は [.ai/rationale/karte-module-split.md](../.ai/rationale/karte-module-split.md)。
"""

from . import model


def open_ids(karte: model.Karte) -> set:
    return {item.id for item in karte.open_findings()}


def invalid_distinct_refs(karte: model.Karte, seen: set, finding_id: str, item) -> list:
    """``distinct_from`` の参照先が実在するか（K-05 のエスケープハッチを監査可能に保つ）。

    名指しできるのは台帳にある finding か、同じレポート内で先に現れた finding だけ。
    実在しない ID や自分自身の名指しは、重複判定を無効化するだけの呪文になるので拒否する。
    """
    errors = []
    for other in item.distinct_from:
        if other == finding_id:
            errors.append(f"{item.lineno} 行目: distinct_from に自分自身は書けない: {other}")
        elif karte.finding(other) is None and other not in seen:
            errors.append(
                f"{item.lineno} 行目: distinct_from が指す finding ID が実在しない: {other}"
                "（台帳にあるか、同じレポートで先に現れた ID だけを名指しできる）"
            )
    return errors


def find_duplicate(karte: model.Karte, accepted, item):
    """新規採番しようとしている指摘が、既存の未解消 finding の焼き直しでないかを見る。

    ``item.distinct_from`` で名指しされた相手だけを比較から外す（K-05）。閾値
    （:data:`model.DUPLICATE_SIMILARITY_THRESHOLD`）は据え置く。
    """
    exempt = set(item.distinct_from)
    for finding in karte.open_findings():
        if finding.id not in exempt and model.is_same_finding(
            item.summary, item.locus, finding.summary, finding.locus
        ):
            return finding.id
    for entry in accepted:
        if entry.finding_id not in exempt and model.is_same_finding(
            item.summary, item.locus, entry.item.summary, entry.item.locus
        ):
            return entry.finding_id
    return None


def absent_open_ids(previously_open: set, accepted) -> list:
    """前ラウンド未解消なのに今回のレポートに再掲されていない finding ID（K-06）。"""
    return sorted(
        previously_open - {entry.finding_id for entry in accepted},
        key=lambda fid: model.parse_finding_id(fid)[1],
    )
