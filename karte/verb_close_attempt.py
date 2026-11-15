"""verb_close_attempt の責務。詳細は .ai/rationale/karte-module-split.md。"""
from . import karte_loader, model, paths, pointer_completion, repo_roots
from . import touched as touched_mod
from .close_attempt_report import print_result, print_saturation
from .close_attempt_target import resolve_close_attempt_number, validate_outcome
from .errors import KarteUsageError
from .exit_codes import EXIT_OK
from .verb_boundary import fail_close

@fail_close(locked=True)
def cmd_close_attempt(args, repo_root) -> int:
    issue = pointer_completion.resolve_issue(args, repo_root)
    path, karte = karte_loader.load_karte(repo_root, issue)
    number = resolve_close_attempt_number(args, karte)
    attempt = karte.attempt(number)
    if attempt is None:
        raise KarteUsageError(f"Attempt {number} がカルテに無い（先に `append` する）")
    if karte.results_for(number):
        raise KarteUsageError(
            f"Attempt {number} には既に Result がある（既存ブロックは書き換えない＝追記のみ）"
        )

    outcome = validate_outcome(args.outcome)

    if args.diff_file:
        diff_path = paths.resolve_within_repo(args.diff_file, repo_root)
        diff_text = paths.read_text(diff_path)
    else:
        # 台帳（repo_root）ではなく呼び出し元 worktree で diff を測る（Issue #437・
        # 混同すると isolated worktree の commit を見失う）。
        diff_text = touched_mod.git_diff(repo_roots.invoking_worktree(), args.base)
    measured = model.check_list(touched_mod.parse_diff(diff_text), "touched")

    if not measured and outcome != "no-change":
        raise KarteUsageError(
            "実測 touched-set が空（diff が空）。"
            "--base（既定 HEAD）が対象の変更を含む範囲を正しく指しているか、"
            "または --diff-file の内容を確認して明示すること。"
            "差分なしで解消と判定する場合は --outcome no-change を指定する"
            "（Issue #355）"
        )

    finding_ids = (
        model.validate_finding_ids(args.finding_ids) if args.finding_ids else list(attempt.finding_ids)
    )
    unknown = [fid for fid in finding_ids if karte.finding(fid) is None]
    if unknown:
        raise KarteUsageError(f"未知の finding ID: {', '.join(unknown)}")

    result = model.Result(
        attempt=number,
        finding_ids=finding_ids,
        touched=measured,
        outcome=outcome,
        note=model.check_scalar(args.note or "", "note"),
    )
    paths.append_text(path, "\n" + model.render_result(result))

    print_result(issue, number, result, attempt, measured)
    print_saturation(path, number)
    return EXIT_OK
