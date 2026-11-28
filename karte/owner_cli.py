"""主文脈専用の verb ``activate`` / ``decide``。"""

from . import ac_snapshot_binding, handoff_header, karte_rounds, model, owner_decision, override_gate, paths, review_attempt_history, review_expectation, scope_ledger, scope_ledger_repair
from .active_pointer import write_active
from .errors import KarteNotFound, KarteUsageError
from .exit_codes import EXIT_OK
from .int_args import require_ascii_int
from .owner_cli_parser import register as _register_parser
from .karte_loader import load_karte
from .pointer_completion import resolve_issue
from .verb_boundary import fail_close
from .vocabulary import DIAGNOSIS_OWNERS


@fail_close(locked=True)
def cmd_activate(args, repo_root) -> int:
    """進行ポインタを対象 Issue の取り込み済み最新 round へ向ける。"""
    issue = paths.validate_issue(args.issue)
    expected = review_expectation.from_args(args, issue)
    if getattr(args, "repair_declared_scope", False):
        if expected is not None:
            raise KarteUsageError("--repair-declared-scope と review envelope 引数は同時に指定できない")
        dropped = scope_ledger_repair.repair(issue, repo_root)
        print(f"=== activate --repair-declared-scope: issue-{issue} 除いた壊れた行 {len(dropped)} 件 ===")
        for line in dropped:
            print(f"  {line}")
        return EXIT_OK
    try:
        last = karte_rounds.last_round(load_karte(repo_root, issue)[1])
    except KarteNotFound:
        last = 0
    next_number = require_ascii_int(last + 1, KarteUsageError("次の round が桁数の上限を超える"))
    snapshot_file = getattr(args, "ac_snapshot_file", None)
    legacy = bool(getattr(args, "legacy_finding_only", False))
    if snapshot_file and expected is None:
        raise KarteUsageError("--ac-snapshot-file は review envelope 期待値と同時指定する")
    if legacy and (expected is None or snapshot_file):
        raise KarteUsageError("--legacy-finding-only はreview envelopeのみ・AC snapshotとの併用禁止")
    if expected is not None and not snapshot_file and not ac_snapshot_binding.allows_finding_only(expected, legacy):
        raise KarteUsageError("implementationのreview envelopeにはAC snapshot必須（旧形式は--legacy-finding-onlyを明示）")
    snapshot = ac_snapshot_binding.stage(repo_root, issue, next_number, snapshot_file) if snapshot_file else None
    revoked = review_attempt_history.for_activation(repo_root, issue, last, expected, snapshot, legacy)
    if snapshot is not None:
        write_active(repo_root, issue, last, expected, ac_snapshot=snapshot,
                     revoked_review_expectations=revoked)
    elif legacy:
        write_active(repo_root, issue, last, expected, legacy_finding_only=True,
                     revoked_review_expectations=revoked)
    else:
        write_active(repo_root, issue, last, expected,
                     revoked_review_expectations=revoked)  # envelope無しの主文脈経路
    print(f"=== activate: issue-{issue} round {last}（次の ingest-reviewer は round {next_number}）===")
    if expected is not None:
        print(f"  review envelope の期待値を記録（run_id={expected['run_id']} phase={expected['phase']}・"
              "取り込み成功で消える・待機中は主文脈の ingest-review を拒否）")
        if snapshot is not None:
            print(f"  AC snapshot: {snapshot['source']} count={snapshot['count']} sha256={snapshot['digest']}")
        print("  レビューアの handoff 先頭へそのまま置くヘッダ（dispatch prompt に渡す）:")
        print("  " + handoff_header.render_header(next_number, expected))
    return EXIT_OK


@fail_close(locked=True)
def cmd_decide(args, repo_root) -> int:
    issue = resolve_issue(args, repo_root)
    options = {
        "disposition": args.disposition, "deferred_to": args.deferred_to,
        "waived_by": args.waived_by, "waived_reason": args.waived_reason,
    }
    path, karte = load_karte(repo_root, issue)
    override_ref = getattr(args, "override_ref", None)
    if override_ref:
        override_gate.require_ref(repo_root, override_ref)
    lines = owner_decision.record_decision(
        karte, args.finding, options, args.scope, override_ref,
        getattr(args, "diagnosis_owner", None),
    )
    owner_scope_saved = False
    if args.scope:
        scope_ledger.record_owner(issue, repo_root, karte_rounds.last_round(karte), args.finding, args.scope)
        owner_scope_saved = True
    try:
        owner_decision.write_karte(path, karte)
    except OSError as exc:
        if owner_scope_saved:
            raise OSError(f"{exc}（scope のオーナー印は保存済み。再度 decide か ingest で台帳へ反映される）") from exc
        raise
    print(f"=== decide: {args.finding} ===")
    print("  " + " / ".join(lines))
    return EXIT_OK



def register(subparsers, add_issue) -> None:
    _register_parser(subparsers, add_issue, cmd_activate, cmd_decide)
