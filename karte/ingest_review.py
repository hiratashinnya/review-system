"""``ingest-review`` / ``ingest-reviewer`` 共通の取り込み本体（共有 writer lock の内側から呼ぶ）。

設計理由（K-06 ほか）は [.ai/rationale/karte-module-split.md](../.ai/rationale/karte-module-split.md)。
"""

import sys

from . import (
    ingest_accept, ingest_apply, ingest_checks, ingest_notes, ingest_report, karte_rounds, model, paths,
    review_expectation, scope_ledger, scope_origin,
)
from .active_pointer import write_active
from .errors import KarteUsageError
from .exit_codes import EXIT_ERROR
from .ingest_types import IngestResult
from .reviewer_policy import ReviewerIngestPolicy, ignore_owner_keys


def ingest_locked(repo_root, issue, round_no, report_text, policy=None, *, allow_same_round=False) -> int:
    """検証で拒否したら台帳・ポインタを書かず ``EXIT_ERROR``（4。``tmp/_karte/`` と ``.writer.lock`` は残る）。通れば台帳を置き換えて ``EXIT_OK``。

    ``policy`` がある場合と申告原本がある場合はオーナー決定を保護する。レビューア本人の取り込みで
    再掲漏れがあれば台帳は書くが ``EXIT_INCOMPLETE``（:func:`ingest_notes.exit_code_for`）。
    """
    if policy is None:
        review_expectation.refuse_main_context_ingest(repo_root, issue)  # レビューア本人の取り込み待ちは迂回させない
    if policy is None and scope_ledger.exists(issue, repo_root):
        policy = ReviewerIngestPolicy(repo_root, issue, round_no, record_declarations=False)
    path = paths.karte_path(issue, repo_root, create_dir=True)
    karte = model.parse(paths.read_text(path)) if path.is_file() else model.new_karte(issue)
    last_round = karte_rounds.last_round(karte)
    if policy is not None and policy.record_declarations and allow_same_round and round_no != last_round:
        raise KarteUsageError(
            f"明示した --round は台帳の最新ラウンドと同じ値に限る（最新は {last_round}・指定は {round_no}）"
        )
    same_round_allowed = policy is not None and (not policy.record_declarations or allow_same_round)
    if round_no < last_round or (round_no == last_round and not same_round_allowed):
        raise KarteUsageError(
            f"round は単調増加させる（取り込み済みの最新ラウンドは {last_round}・"
            f"指定は {round_no}）。同じラウンドの再取り込みは、保護モードの主文脈 ingest-review と"
            "レビューアの --round 明示（台帳の最新ラウンドと同じ値）以外では拒否する。"
            "回復は再取り込みではなく karte/README.md「進行ポインタの書込みが台帳より後に失敗した窓」を参照"
        )

    warnings = []
    if policy:
        report_text, warnings = ignore_owner_keys(report_text)
    review = model.parse_review(report_text, issue)
    previously_open = karte.open_ids()
    collected = ingest_accept.collect_accepted(karte, review, issue)
    errors = list(collected.errors)
    if policy and not policy.record_declarations:
        repeated = sorted({
            entry.finding_id for entry in collected.accepted
            if karte.finding(entry.finding_id) is not None
        })
        if repeated:
            errors.append(
                "保護モードの ingest-review は新規 finding の追記専用。既存 finding の変更は "
                "decide（オーナー決定）か、レビューア本人の ingest-reviewer で行う: "
                + ", ".join(repeated)
            )

    # K-06: 不在は解消ではない。保護モードでは変更せず引き継ぎ、それ以外は拒否する。
    absent = ingest_checks.absent_open_ids(previously_open, collected.accepted)
    if absent and policy:
        warnings.append("再掲されなかった未解消 finding を引き継ぎ: " + ", ".join(absent))
    elif absent:
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
    if policy:
        for finding in karte.findings:
            if finding.id in policy.owner_scopes:
                finding.scope = policy.owner_scopes[finding.id]
    karte.findings.sort(key=lambda item: item.seq)
    origin = scope_origin.begin(issue, repo_root, collected.accepted, "reviewer" if policy and policy.record_declarations else "main", round_no)
    if policy:
        policy.persist(round_no)  # 台帳より先に原本を残す
    paths.write_text_atomic(path, model.dumps(karte))
    scope_origin.commit(issue, repo_root, origin)
    write_active(repo_root, issue, round_no)
    for warning in warnings:
        print(f"警告: {warning}", file=sys.stderr)
    ingest_report.print_report(
        IngestResult(karte, path, issue, round_no, collected.accepted, outcome)
    )
    for warning in warnings:
        print(f"  警告: {warning}")
    ingest_notes.print_policy_notes(policy)
    return ingest_notes.exit_code_for(policy, karte, absent)
