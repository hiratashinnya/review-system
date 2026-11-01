"""主文脈専用の verb ``activate`` / ``decide``（どのロールの許可集合にも入れない・Issue #375）。"""

from . import owner_decision, paths, scope_ledger, scope_ledger_repair
from .active_pointer import write_active
from .errors import KarteNotFound
from .exit_codes import EXIT_OK
from .verb_support import fail_close, load_karte, repo_root_of, resolve_issue


def _last_round(karte) -> int:
    return max((r for item in karte.findings for r in item.rounds), default=0)


@fail_close
def cmd_activate(args) -> int:
    """進行ポインタを対象 Issue へ向ける（round は台帳の取り込み済み最新。台帳が無ければ 0＝未取込）。

    ``--repair-declared-scope`` は壊れた申告 scope の原本を復旧する（ポインタは触らない）。
    """
    repo_root = repo_root_of(args)
    issue = paths.validate_issue(args.issue)
    if getattr(args, "repair_declared_scope", False):
        with paths.writer_lock(repo_root):
            dropped = scope_ledger_repair.repair(issue, repo_root)
        print(f"=== activate --repair-declared-scope: issue-{issue} 除いた壊れた行 {len(dropped)} 件 ===")
        for line in dropped:
            print(f"  {line}")
        return EXIT_OK
    with paths.writer_lock(repo_root):
        try:
            last = _last_round(load_karte(repo_root, issue)[1])
        except KarteNotFound:  # 台帳が無い＝初回
            last = 0
        write_active(repo_root, issue, last)
    print(f"=== activate: issue-{issue} round {last}（次の ingest-reviewer は round {last + 1}）===")
    return EXIT_OK


@fail_close
def cmd_decide(args) -> int:
    repo_root = repo_root_of(args)
    issue = resolve_issue(args, repo_root)
    options = {
        "disposition": args.disposition, "deferred_to": args.deferred_to,
        "waived_by": args.waived_by, "waived_reason": args.waived_reason,
    }
    with paths.writer_lock(repo_root):
        path, karte = load_karte(repo_root, issue)
        lines = owner_decision.record_decision(karte, args.finding, options, args.scope)
        owner_decision.write_karte(path, karte)
        if args.scope:  # 以後の ingest-reviewer が台帳の scope を上書きしないための印（台帳の後に書く）
            scope_ledger.record_owner(issue, repo_root, _last_round(karte), args.finding, args.scope)
    print(f"=== decide: {args.finding} ===")
    print("  " + " / ".join(lines))
    return EXIT_OK
