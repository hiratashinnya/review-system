"""主文脈専用の verb ``activate`` / ``decide``。"""

from . import karte_rounds, model, owner_decision, paths, scope_ledger, scope_ledger_repair
from .active_pointer import write_active
from .errors import KarteNotFound, KarteUsageError
from .exit_codes import EXIT_OK
from .int_args import require_ascii_int
from .karte_loader import load_karte
from .pointer_completion import resolve_issue
from .verb_boundary import fail_close


@fail_close(locked=True)
def cmd_activate(args, repo_root) -> int:
    """進行ポインタを対象 Issue の取り込み済み最新 round へ向ける。"""
    issue = paths.validate_issue(args.issue)
    if getattr(args, "repair_declared_scope", False):
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
    write_active(repo_root, issue, last)
    print(f"=== activate: issue-{issue} round {last}（次の ingest-reviewer は round {next_number}）===")
    return EXIT_OK


@fail_close(locked=True)
def cmd_decide(args, repo_root) -> int:
    issue = resolve_issue(args, repo_root)
    options = {
        "disposition": args.disposition, "deferred_to": args.deferred_to,
        "waived_by": args.waived_by, "waived_reason": args.waived_reason,
    }
    path, karte = load_karte(repo_root, issue)
    lines = owner_decision.record_decision(karte, args.finding, options, args.scope)
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
    activate = subparsers.add_parser("activate", help="進行ポインタを Issue に向ける（主文脈専用）")
    activate.add_argument("--issue", required=True, help="Issue 番号")
    activate.add_argument(
        "--repair-declared-scope", action="store_true",
        help="壊れた申告 scope の原本の行を除いて復旧する（元は .bak* に世代を分けて残す）",
    )
    activate.set_defaults(func=cmd_activate)
    decide = subparsers.add_parser("decide", help="オーナー決定を台帳へ記録する（主文脈専用）")
    add_issue(decide)
    decide.add_argument("--finding", required=True, help="対象の finding ID")
    decide.add_argument("--disposition", choices=list(model.DISPOSITIONS))
    decide.add_argument("--deferred-to")
    decide.add_argument("--waived-by")
    decide.add_argument("--waived-reason")
    decide.add_argument("--scope", help="オーナーが覆した scope（in|out）")
    decide.set_defaults(func=cmd_decide)
