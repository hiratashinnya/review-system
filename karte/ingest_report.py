"""取り込み結果を標準出力へ整形する。"""

from . import ingest_checks
from .ingest_types import IngestResult


def print_report(result: IngestResult) -> None:
    karte, outcome = result.karte, result.outcome
    created = outcome.created
    print(f"=== ingest-review: issue-{result.issue} round {result.round_no} ===")
    print(
        f"  取り込み: {len(result.accepted)} 件"
        f"（新規 {len(created)} / 再掲 {len(result.accepted) - len(created)}）"
    )
    if created:
        print(f"  新規採番: {', '.join(created)}")
    if outcome.resolved:
        print(f"  解消（レポートで `status: resolved` と明示された）: {', '.join(sorted(outcome.resolved))}")
    if outcome.excluded:
        print(f"  重複判定の明示的除外（distinct_from）: {'; '.join(outcome.excluded)}")
    print(f"  未解消: {', '.join(sorted(ingest_checks.open_ids(karte))) or '(なし)'}")
    out_of_scope = sorted(item.id for item in karte.open_findings() if item.scope == "out")
    if out_of_scope:
        # Issue #495: スコープ外の申告も同じ列に入ったことを取り込み時点で見せる。
        print(f"  うち scope: out（実害判定・verdict の免除にはならない）: {', '.join(out_of_scope)}")
    undecided = sorted(item.id for item in karte.undecided_findings())
    if undecided:
        print(
            "  実害あり・disposition 未決定（clean を妨げる。fix-here / deferred / waived を決める）: "
            + ", ".join(undecided)
        )
    print(f"  カルテ: {result.path}")
