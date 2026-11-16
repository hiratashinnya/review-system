"""verb_check の責務。詳細は .ai/rationale/karte-module-split.md。"""
import sys
from . import karte_loader, pointer_completion, override_gate
from .check_diagnosis import exemption_reason
from .exit_codes import EXIT_ERROR, EXIT_OK
from .verb_boundary import fail_close

@fail_close(locked=False)
def cmd_check(args, repo_root) -> int:
    """診断網羅と全 Attempt のクローズを検査する。"""
    issue = pointer_completion.resolve_issue(args, repo_root)
    _path, karte = karte_loader.load_karte(repo_root, issue)
    round_no = pointer_completion.resolve_round(
        args, repo_root, issue, pointer_completion.MissingRoundHint.RUN_INGEST_FIRST
    ).number

    attempts = [item for item in karte.attempts if item.round == round_no]
    open_items = karte.open_findings()
    pending = (override_gate.pending(karte, repo_root) if any(
        f.harm == "none" and f.disposition == "waived" for f in open_items
    ) else {})
    excused_by_id = {
        item.id: reason for item in open_items if round_no in item.rounds
        if (reason := exemption_reason(item, pending)) is not None
    }
    expected = sorted(
        item.id for item in karte.remediation_findings()
        if round_no in item.rounds and item.id not in excused_by_id
    )
    legacy_excused = [
        f"{fid}（{reason}）" for fid, reason in sorted(excused_by_id.items())
        if reason in ("deferred", "waived")
    ]
    assigned_excused = [
        f"{fid}（{reason}）" for fid, reason in sorted(excused_by_id.items())
        if reason not in ("deferred", "waived")
    ]
    print(f"=== check: issue-{issue} round {round_no} ===")
    if not attempts:
        print(
            f"NG: round {round_no} の Attempt が 1 件も無い"
            f"（診断が要る未解消 finding: {', '.join(expected) or '(なし)'}）",
            file=sys.stderr,
        )
        return EXIT_ERROR
    covered = {fid for item in attempts for fid in item.finding_ids}
    missing = [fid for fid in expected if fid not in covered]
    print(f"  Attempt: {', '.join(str(item.number) for item in attempts)}")
    print(f"  診断が要る未解消 finding: {', '.join(expected) or '(なし)'}")
    if legacy_excused:
        print(
            "  診断不要（disposition で当該 PR では処置しないと決定済み・status は open のまま）: "
            + ", ".join(legacy_excused)
        )
    if assigned_excused:
        print(
            "  診断不要（是正担当の診断対象外。status の判定は変更しない）: "
            + ", ".join(assigned_excused)
        )
    if missing:
        print(f"NG: 診断されていない未解消 finding: {', '.join(missing)}", file=sys.stderr)
        return EXIT_ERROR

    pending = [
        item.number
        for item in karte.attempts
        if not karte.results_for(item.number)
    ]
    if pending:
        print(
            "NG: 未クローズの Attempt が残っている: "
            + ", ".join(str(number) for number in pending)
            + "（実測 touched-set が供給されず、類似判定の実測信号が働かないまま"
            "同種の試行を続けられてしまう）",
            file=sys.stderr,
        )
        for number in pending:
            print(
                f"  実行: python3 -m karte close-attempt --issue {issue} "
                f"--attempt {number} --outcome <fixed|partial|no-change|regressed>",
                file=sys.stderr,
            )
        return EXIT_ERROR

    print("OK: 当該ラウンドの Attempt が未解消 finding を網羅し、全 Attempt がクローズ済み")
    return EXIT_OK
