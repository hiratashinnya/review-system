"""``ingest-review`` の取り込み本体（共有 writer lock を取った呼び出し元から呼ぶ）。

設計理由（K-06 ほか）は [.ai/rationale/karte-module-split.md](../.ai/rationale/karte-module-split.md)。
"""

import sys

from . import ingest_accept, ingest_apply, ingest_checks, ingest_report, model, paths, scope_ledger
from .active_pointer import write_active
from .errors import KarteUsageError
from .exit_codes import EXIT_ERROR, EXIT_OK
from .ingest_types import IngestResult


def ingest_locked(repo_root, issue, round_no, report_text, policy=None) -> int:
    """検証に 1 件でも掛かれば**一切書かず** ``EXIT_ERROR``。通れば台帳を置き換えて ``EXIT_OK``。

    ``policy``＝レビューア本人の取り込み（:mod:`karte.reviewer_policy`）の追加規則。
    """
    if policy is None and scope_ledger.exists(issue, repo_root):
        # ingest-reviewer の原本がある Issue へ主文脈が取り込むと、`decide` で記録した
        # オーナー決定がレポートの値で上書きされる。二経路を併存させない。
        raise KarteUsageError(
            f"issue-{issue} は ingest-reviewer で取り込み済み（申告 scope の原本がある）。"
            "`ingest-review` は使えない（オーナー決定は `decide` で記録する）"
        )
    path = paths.karte_path(issue, repo_root, create_dir=True)
    karte = model.parse(paths.read_text(path)) if path.is_file() else model.new_karte(issue)

    last_round = max((r for item in karte.findings for r in item.rounds), default=0)
    if round_no <= last_round:
        raise KarteUsageError(
            f"round は単調増加させる（取り込み済みの最新ラウンドは {last_round}・"
            f"指定は {round_no}）。同じラウンドの再取り込みは台帳の状態遷移を壊す"
        )

    review = model.parse_review(report_text, issue)
    previously_open = ingest_checks.open_ids(karte)
    collected = ingest_accept.collect_accepted(karte, review, issue)
    errors = (policy.check(review) if policy else []) + list(collected.errors)

    # K-06: 「不在＝解消」を廃止する。前ラウンド時点で未解消だった finding が 1 件でも
    # 欠けていれば取り込みごと拒否する。欠けている ID は全て列挙する（1 件ずつ往復させない）。
    absent = ingest_checks.absent_open_ids(previously_open, collected.accepted)
    if absent:
        errors.append(
            "前ラウンドで未解消の finding が今回のレポートに再掲されていない: "
            f"{', '.join(absent)}"
            "（不在は解消ではない。解消したなら当該 ID のブロックを `status: resolved` で"
            "再掲し、未解消なら `status: open` のまま再掲する）"
        )
    if errors:
        for line in errors:
            print(f"拒否（fail-close）: {line}", file=sys.stderr)
        return EXIT_ERROR

    outcome = ingest_apply.apply_accepted(karte, collected.accepted, round_no, policy)
    karte.findings.sort(key=lambda item: item.seq)
    if policy:
        policy.persist(round_no)  # 台帳より先に原本を残す（台帳が未更新なら同じ round で再試行できる）
    paths.write_text_atomic(path, model.dumps(karte))
    write_active(repo_root, issue, round_no)
    ingest_report.print_report(
        IngestResult(karte, path, issue, round_no, collected.accepted, outcome)
    )
    return EXIT_OK
