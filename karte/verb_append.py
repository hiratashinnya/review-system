"""verb_append の責務。詳細は .ai/rationale/karte-module-split.md。"""
from . import active_pointer, int_args, karte_loader, model, paths, pointer_completion, similarity
from .errors import KarteUsageError
from .exit_codes import EXIT_OK, EXIT_SATURATED
from .saturation_groups import priors_for as _priors_for
from .verb_boundary import fail_close

@fail_close(locked=True)
def cmd_append(args, repo_root) -> int:
    issue = pointer_completion.resolve_issue(args, repo_root)
    path, karte = karte_loader.load_karte(repo_root, issue)
    active = active_pointer.read_active(repo_root)
    if args.round is not None:
        round_no = int_args.parse_int(args.round, "round")
    else:
        round_no = pointer_completion.recorded_round(active, issue) or max(
            (r for item in karte.findings for r in item.rounds), default=1
        )

    finding_ids = model.validate_finding_ids(args.finding_ids)
    unknown = [fid for fid in finding_ids if karte.finding(fid) is None]
    if unknown:
        raise KarteUsageError(
            f"未知の finding ID: {', '.join(unknown)}"
            "（先に `ingest-review` で台帳へ取り込むこと）"
        )
    attempt = model.Attempt(
        number=karte.next_attempt_number(),
        round=round_no,
        finding_ids=finding_ids,
        root_cause=model.validate_slug(args.root_cause, "root_cause"),
        change_kind=model.validate_change_kind(args.change_kind),
        targets=model.validate_targets(args.targets),
        diagnosis=model.check_scalar(args.diagnosis or "", "diagnosis"),
    )

    new_view = similarity.AttemptView(
        number=attempt.number,
        root_cause=attempt.root_cause,
        change_kind=attempt.change_kind,
        targets=tuple(attempt.targets),
        touched=(),
    )
    priors = _priors_for(karte, finding_ids)
    hits = similarity.find_hits(new_view, priors)
    if similarity.is_saturated(hits):
        open_ids = karte.open_ids()
        open_targets = {fid for fid in finding_ids if fid in open_ids}
        print(similarity.build_directive(new_view, hits, open_targets).text())
        print(
            "（Attempt は書き込んでいない。転換したアプローチで `append` をやり直すこと）"
        )
        return EXIT_SATURATED

    paths.append_text(path, "\n" + model.render_attempt(attempt))
    print(f"=== append: issue-{issue} Attempt {attempt.number}（round {round_no}）===")
    print(f"  finding_ids: {', '.join(attempt.finding_ids)}")
    print(f"  root_cause: {attempt.root_cause} / change_kind: {attempt.change_kind}")
    print(f"  targets: {', '.join(attempt.targets)}")
    if hits:
        print(
            "  注意: 過去 Attempt "
            + ", ".join(str(hit.prior) for hit in hits)
            + " と類似（"
            + " / ".join(sorted({name for hit in hits for name in hit.signals}))
            + "）。次に同種を出すと拒否される"
        )
    print(f"  カルテ: {path}")
    return EXIT_OK
