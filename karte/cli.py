"""karte の verb 実装（``python3 -m karte <verb>``・標準ライブラリのみ）。

verb:
  ``ingest-review``  レビューレポートを ``## Findings`` へ取り込む（ID 重複・未知 ID・
                     harm 欄欠落・同一指摘への ID 再発番を検証）。
  ``render``         「Prior attempts（DO NOT repeat these）」＋未解消 finding 一覧。
                     類似グループが飽和していれば転換指令も合成する。
  ``append``         Attempt をスキーマ検証つきで追記。類似飽和なら**書き込まず**拒否し、
                     反復された root_cause / targets を名指しした転換指令を stdout に返す。
  ``close-attempt``  修正後の実測 touched-set を ``### Result k`` として追記する
                     （実測信号の供給源。Attempt ブロック自体は書き換えない）。
  ``check``          当該ラウンドの Attempt が存在し未解消 finding を網羅しているか。
  ``status``         実害あり残存 / 全件実害なし / 無進捗（同一 finding が3ラウンド連続未解消）
                     を機械判定する（エスカレーション条件）。

終了コード（``dsv2`` に合わせる）:
  0 OK ／ 2 未検出 ／ 3 類似飽和（append 拒否）／ 4 前提違反・検証失敗（fail-close）。

``repo_root`` は **公開 CLI フラグとしては持たない**内部専用パラメータ
（``args`` に属性として渡されたときだけ使う）。実運用は常にリポジトリルートで動くため、
公開フラグは信頼境界を広げるだけの攻撃面になる（``dsv2/cli.py`` の
``cmd_clean_tmp`` と同じ判断・issue #276 round-2）。テストは ``argparse.Namespace`` を
直接組み立てて各 ``cmd_*`` を呼ぶ。

依存仕様: :mod:`karte` の docstring（Issue #307）。
"""

from __future__ import annotations

import argparse
import functools
import json
import sys
from pathlib import Path

from . import model, paths, similarity, touched as touched_mod
from .model import KarteFormatError
from .paths import KartePathError
from .touched import TouchedError

EXIT_OK = 0
EXIT_NOT_FOUND = 2
EXIT_SATURATED = 3
EXIT_ERROR = 4

STALL_ROUNDS = 3  # 同一 finding_id がこのラウンド数連続で未解消なら「無進捗」

# linked worktree（`issue-implementer` 等の isolated worktree）でも main worktree の
# `tmp/_karte/` へ収束させる（K-01）。`.git` がファイルなら `gitdir:` を辿る
# `paths.main_worktree_root`（ガードは downstream の `_resolved_root` 等で必ず掛かる）。
_REPO_ROOT = paths.main_worktree_root(Path(__file__).resolve().parent.parent)


class KarteUsageError(Exception):
    """前提違反（存在しない Attempt・未知 finding ID 等）。fail-close で何も書かない。"""


class KarteNotFound(KarteUsageError):
    """対象のカルテがまだ存在しない（未検出＝EXIT_NOT_FOUND）。"""


def _fail_close(func):
    """``cmd_*`` を「例外を投げず終了コードを返す」境界にする。

    verb 単位が終了コードの境界（＝呼び出し側は ``main`` 経由でも直呼びでも同じ
    fail-close 挙動を得る）。``main`` にだけ ``try/except`` を置くと、フックや
    テストのように ``cmd_*`` を直接呼ぶ経路では例外が素通りし、「拒否されたのに
    exit code が返らない」＝判定不能になる。ガードの効力を呼び出し経路に依存させない。
    """

    @functools.wraps(func)
    def wrapper(args) -> int:
        try:
            return func(args)
        except KarteNotFound as exc:
            print(f"未検出: {exc}", file=sys.stderr)
            return EXIT_NOT_FOUND
        except (KarteUsageError, KartePathError, KarteFormatError, TouchedError, OSError) as exc:
            print(f"拒否（fail-close）: {exc}", file=sys.stderr)
            return EXIT_ERROR

    return wrapper


# --- 共通ヘルパ --------------------------------------------------------------


def _repo_root(args) -> Path:
    override = getattr(args, "repo_root", None)
    return Path(override).resolve() if override else _REPO_ROOT


def _read_active(repo_root) -> dict:
    try:
        path = paths.active_path(repo_root)
    except KartePathError:
        return {}
    if not path.is_file():
        return {}
    try:
        data = json.loads(paths.read_text(path))
    except (ValueError, KartePathError):
        return {}
    return data if isinstance(data, dict) else {}


def _write_active(repo_root, issue: int, round_no: int) -> None:
    path = paths.active_path(repo_root, create_dir=True)
    paths.write_text_atomic(
        path, json.dumps({"issue": int(issue), "round": int(round_no)}, ensure_ascii=False) + "\n"
    )


def _resolve_issue(args) -> int:
    """``--issue`` 省略時は進行ポインタ ``tmp/_karte/active.json`` を使う。"""
    if getattr(args, "issue", None) is not None:
        return paths.validate_issue(args.issue)
    active = _read_active(_repo_root(args))
    if "issue" not in active:
        raise KarteUsageError(
            "--issue が未指定で、進行ポインタ tmp/_karte/active.json も無い"
            "（先に `ingest-review --issue N --round R` を実行する）"
        )
    return paths.validate_issue(active["issue"])


def _validate_round(value) -> int:
    text = str(value)
    if not text.isdigit() or int(text) < 1:
        raise KarteUsageError(f"round は 1 以上の整数: {value!r}")
    return int(text)


def _validate_attempt_number(value) -> int:
    """``--attempt`` を検証する（``_validate_round`` と同型・K-03）。

    ``int(args.attempt)`` を無検証で呼ぶと非数値入力で ``ValueError`` が送出され、
    ``_fail_close`` の捕捉対象外（文書化された終了コード ``{0,2,3,4}`` の外）に漏れる。
    """
    text = str(value)
    if not text.isdigit() or int(text) < 1:
        raise KarteUsageError(f"attempt は 1 以上の整数: {value!r}")
    return int(text)


def _load(args, issue: int):
    """カルテを読み込む。存在しなければ :class:`KarteNotFound`（＝EXIT_NOT_FOUND）。

    「まだ作られていない」（置き場ごと無い＝:class:`paths.KarteMissing`）は**未検出**であって
    ガード違反ではない。両者を同じ EXIT_ERROR に潰すと、``render`` を先に叩く運用側が
    「カルテが未作成」と「触ってはならないパス」を区別できない。
    """
    try:
        path = paths.karte_path(issue, _repo_root(args))
    except paths.KarteMissing as exc:
        raise KarteNotFound(
            f"{exc}（先に `ingest-review --issue {issue} --round 1` を実行する）"
        ) from None
    if not path.is_file():
        raise KarteNotFound(
            f"カルテが無い: {path}（先に `ingest-review --issue {issue} --round 1` を実行する）"
        )
    return path, model.parse(paths.read_text(path))


def _view_of(karte: model.Karte, attempt: model.Attempt) -> similarity.AttemptView:
    return similarity.AttemptView(
        number=attempt.number,
        root_cause=attempt.root_cause,
        change_kind=attempt.change_kind,
        targets=tuple(attempt.targets),
        touched=tuple(karte.touched_of(attempt.number)),
    )


def _open_ids(karte: model.Karte) -> set:
    return {item.id for item in karte.open_findings()}


def _priors_for(karte: model.Karte, finding_ids) -> list:
    """``finding_ids`` のうち **未解消** のものを共有する過去 Attempt の投影を返す。"""
    relevant = {fid for fid in finding_ids if fid in _open_ids(karte)}
    views = []
    for attempt in karte.attempts:
        if relevant & set(attempt.finding_ids):
            views.append(_view_of(karte, attempt))
    return views


def _stalled_ids(karte: model.Karte) -> list:
    return sorted(
        item.id
        for item in karte.open_findings()
        if item.max_consecutive_rounds() >= STALL_ROUNDS
    )


def _saturated_clusters(karte: model.Karte) -> list:
    """未解消 finding を共有し合う試行群のうち、飽和している類似グループ。"""
    open_ids = _open_ids(karte)
    views = [
        _view_of(karte, attempt)
        for attempt in karte.attempts
        if open_ids & set(attempt.finding_ids)
    ]
    return [
        members
        for members in similarity.cluster(views)
        if len(members) >= similarity.SATURATION_THRESHOLD
    ]


def _cluster_directive(karte: model.Karte, members) -> str:
    """既存クラスタから転換指令を合成する（末尾の試行を「今回」と見なす）。"""
    views = {view.number: view for view in (_view_of(karte, a) for a in karte.attempts)}
    latest = views[members[-1]]
    priors = [views[number] for number in members[:-1]]
    hits = similarity.find_hits(latest, priors)
    if not hits:
        return ""
    attempt = karte.attempt(members[-1])
    open_ids = _open_ids(karte) & set(attempt.finding_ids if attempt else [])
    return similarity.build_directive(latest, hits, open_ids).text()


# --- verb: ingest-review ------------------------------------------------------


@_fail_close
def cmd_ingest_review(args) -> int:
    repo_root = _repo_root(args)
    issue = _resolve_issue(args)
    round_no = _validate_round(args.round)
    report_path = paths.resolve_within_repo(args.source, repo_root)
    report_text = paths.read_text(report_path)

    path = paths.karte_path(issue, repo_root, create_dir=True)
    karte = model.parse(paths.read_text(path)) if path.is_file() else model.new_karte(issue)

    last_round = max((r for item in karte.findings for r in item.rounds), default=0)
    if round_no <= last_round:
        raise KarteUsageError(
            f"round は単調増加させる（取り込み済みの最新ラウンドは {last_round}・"
            f"指定は {round_no}）。同じラウンドの再取り込みは台帳の状態遷移を壊す"
        )

    review = model.parse_review(report_text, issue)

    errors: list = []
    accepted: list = []  # (finding_id, ReviewFinding, is_new)
    seen: set = set()
    next_seq = karte.next_seq()
    for item in review:
        if item.finding_id is None:
            finding_id = model.format_finding_id(issue, next_seq)
            next_seq += 1
            is_new = True
        else:
            finding_id = item.finding_id
            _issue_of_id, seq = model.parse_finding_id(finding_id)
            if karte.finding(finding_id) is not None:
                is_new = False
            elif seq == next_seq:
                next_seq += 1
                is_new = True
            else:
                errors.append(
                    f"{item.lineno} 行目: 未知の finding ID: {finding_id}"
                    f"（台帳に無く、次に採番できるのは {model.format_finding_id(issue, next_seq)}）"
                )
                continue
        if finding_id in seen:
            errors.append(f"{item.lineno} 行目: finding ID がレポート内で重複している: {finding_id}")
            continue
        seen.add(finding_id)

        if is_new:
            duplicate = _find_duplicate(karte, accepted, item)
            if duplicate is not None:
                errors.append(
                    f"{item.lineno} 行目: ID 再発番を検出: {finding_id} は既存の未解消 "
                    f"{duplicate} と同一の指摘（locus/summary が一致）。"
                    "未解消の指摘を再度挙げるときは同じ ID を再利用すること"
                )
                continue
        accepted.append((finding_id, item, is_new))

    if errors:
        for line in errors:
            print(f"拒否（fail-close）: {line}", file=sys.stderr)
        return EXIT_ERROR

    reraised = set()
    created = []
    for finding_id, item, is_new in accepted:
        reraised.add(finding_id)
        finding = karte.finding(finding_id)
        if finding is None:
            finding = model.Finding(id=finding_id)
            karte.findings.append(finding)
            created.append(finding_id)
        finding.status = "open"
        finding.resolved_round = None
        finding.harm = item.harm
        finding.harm_detail = item.harm_detail
        finding.locus = item.locus
        finding.summary = item.summary
        if round_no not in finding.rounds:
            finding.rounds.append(round_no)
        finding.rounds.sort()
        _ = is_new

    resolved = []
    for finding in karte.findings:
        if finding.is_open and finding.id not in reraised:
            finding.status = "resolved"
            finding.resolved_round = round_no
            resolved.append(finding.id)

    karte.findings.sort(key=lambda item: item.seq)
    paths.write_text_atomic(path, model.dumps(karte))
    _write_active(repo_root, issue, round_no)

    print(f"=== ingest-review: issue-{issue} round {round_no} ===")
    print(f"  取り込み: {len(accepted)} 件（新規 {len(created)} / 再掲 {len(accepted) - len(created)}）")
    if created:
        print(f"  新規採番: {', '.join(created)}")
    if resolved:
        print(f"  解消（今回のレポートで再掲されなかった）: {', '.join(sorted(resolved))}")
    print(f"  未解消: {', '.join(sorted(_open_ids(karte))) or '(なし)'}")
    print(f"  カルテ: {path}")
    return EXIT_OK


def _find_duplicate(karte: model.Karte, accepted, item):
    """新規採番しようとしている指摘が、既存の未解消 finding の焼き直しでないかを見る。"""
    for finding in karte.open_findings():
        if model.is_same_finding(item.summary, item.locus, finding.summary, finding.locus):
            return finding.id
    for finding_id, other, _is_new in accepted:
        if model.is_same_finding(item.summary, item.locus, other.summary, other.locus):
            return finding_id
    return None


# --- verb: render -------------------------------------------------------------


@_fail_close
def cmd_render(args) -> int:
    issue = _resolve_issue(args)
    path, karte = _load(args, issue)
    active = _read_active(_repo_root(args))
    round_no = active.get("round") if active.get("issue") == issue else None

    lines = [f"=== Karte: issue-{issue}" + (f" / round {round_no}" if round_no else "") + " ==="]
    lines.append("")
    lines.append("## Prior attempts（DO NOT repeat these）")
    if not karte.attempts:
        lines.append("  (まだ試行なし)")
    for attempt in karte.attempts:
        measured = karte.touched_of(attempt.number)
        lines.append(
            f"  - Attempt {attempt.number} [round {attempt.round}] "
            f"root_cause={attempt.root_cause} change_kind={attempt.change_kind}"
        )
        lines.append(f"      finding_ids: {', '.join(attempt.finding_ids)}")
        lines.append(f"      targets: {', '.join(attempt.targets)}")
        if attempt.diagnosis:
            lines.append(f"      diagnosis: {attempt.diagnosis}")
        if measured:
            lines.append(f"      実測 touched: {', '.join(measured)}")
        for result in karte.results_for(attempt.number):
            note = f" / {result.note}" if result.note else ""
            lines.append(f"      → Result: {result.outcome}{note}")
        if not karte.results_for(attempt.number):
            lines.append("      → Result: (未クローズ。修正後に `close-attempt` で実測を記録する)")

    lines.append("")
    lines.append("## Open findings（未解消）")
    open_findings = karte.open_findings()
    if not open_findings:
        lines.append("  (未解消の指摘なし)")
    for finding in open_findings:
        stalled = " ★無進捗" if finding.max_consecutive_rounds() >= STALL_ROUNDS else ""
        lines.append(
            f"  - {finding.id} [harm={finding.harm}] rounds={finding.rounds}{stalled}"
        )
        lines.append(f"      summary: {finding.summary}")
        lines.append(f"      harm_detail: {finding.harm_detail}")
        if finding.locus:
            lines.append(f"      locus: {finding.locus}")
        related = karte.attempts_for_finding(finding.id)
        if related:
            lines.append(
                "      対応した Attempt: "
                + ", ".join(str(item.number) for item in related)
            )

    clusters = _saturated_clusters(karte)
    if clusters:
        lines.append("")
        lines.append("## 類似グループ飽和（次の Attempt は転換が必要）")
        for members in clusters:
            lines.append(f"  - Attempt {', '.join(str(number) for number in members)} は同種")
            directive = _cluster_directive(karte, members)
            if directive:
                lines.append(directive)

    lines.append("")
    lines.append(f"（カルテ本体: {path}）")
    print("\n".join(lines))
    return EXIT_OK


# --- verb: append -------------------------------------------------------------


@_fail_close
def cmd_append(args) -> int:
    issue = _resolve_issue(args)
    path, karte = _load(args, issue)
    active = _read_active(_repo_root(args))
    if args.round is not None:
        round_no = _validate_round(args.round)
    elif active.get("issue") == issue and active.get("round"):
        round_no = _validate_round(active["round"])
    else:
        round_no = max((r for item in karte.findings for r in item.rounds), default=1)

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
        open_targets = {fid for fid in finding_ids if fid in _open_ids(karte)}
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


# --- verb: close-attempt ------------------------------------------------------


@_fail_close
def cmd_close_attempt(args) -> int:
    issue = _resolve_issue(args)
    path, karte = _load(args, issue)
    number = (
        _validate_attempt_number(args.attempt)
        if args.attempt is not None
        else karte.next_attempt_number() - 1
    )
    attempt = karte.attempt(number)
    if attempt is None:
        raise KarteUsageError(f"Attempt {number} がカルテに無い（先に `append` する）")
    if karte.results_for(number):
        raise KarteUsageError(
            f"Attempt {number} には既に Result がある（既存ブロックは書き換えない＝追記のみ）"
        )

    if args.diff_file:
        diff_path = paths.resolve_within_repo(args.diff_file, _repo_root(args))
        diff_text = paths.read_text(diff_path)
    else:
        diff_text = touched_mod.git_diff(_repo_root(args), args.base)
    measured = model.check_list(touched_mod.parse_diff(diff_text), "touched")

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
        outcome=_validate_outcome(args.outcome),
        note=model.check_scalar(args.note or "", "note"),
    )
    paths.append_text(path, "\n" + model.render_result(result))

    print(f"=== close-attempt: issue-{issue} Attempt {number} ===")
    print(f"  outcome: {result.outcome}")
    print(f"  実測 touched: {', '.join(result.touched) or '(差分なし)'}")
    if not result.touched:
        print("  注意: 差分が空。--base / --diff-file の指定が正しいか確認する")

    karte = model.parse(paths.read_text(path))
    for members in _saturated_clusters(karte):
        if number in members:
            print("")
            print(_cluster_directive(karte, members))
    print(f"  カルテ: {path}")
    return EXIT_OK


def _validate_outcome(value: str) -> str:
    text = model.check_scalar(value, "outcome")
    if text not in model.OUTCOMES:
        raise KarteUsageError(f"outcome は {list(model.OUTCOMES)} のいずれか: {value!r}")
    return text


# --- verb: check --------------------------------------------------------------


@_fail_close
def cmd_check(args) -> int:
    issue = _resolve_issue(args)
    _path, karte = _load(args, issue)
    round_no = _validate_round(args.round)

    attempts = [item for item in karte.attempts if item.round == round_no]
    expected = sorted(
        item.id for item in karte.open_findings() if round_no in item.rounds
    )
    print(f"=== check: issue-{issue} round {round_no} ===")
    if not attempts:
        print(
            f"NG: round {round_no} の Attempt が 1 件も無い"
            f"（未解消 finding: {', '.join(expected) or '(なし)'}）",
            file=sys.stderr,
        )
        return EXIT_ERROR
    covered = {fid for item in attempts for fid in item.finding_ids}
    missing = [fid for fid in expected if fid not in covered]
    print(f"  Attempt: {', '.join(str(item.number) for item in attempts)}")
    print(f"  対象の未解消 finding: {', '.join(expected) or '(なし)'}")
    if missing:
        print(f"NG: 診断されていない未解消 finding: {', '.join(missing)}", file=sys.stderr)
        return EXIT_ERROR
    print("OK: 当該ラウンドの Attempt が未解消 finding を網羅している")
    return EXIT_OK


# --- verb: status -------------------------------------------------------------


def _status_payload(karte: model.Karte) -> dict:
    open_findings = karte.open_findings()
    harmful = [item for item in open_findings if item.harm == "real"]
    if not open_findings:
        verdict = "clean"
    elif harmful:
        verdict = "harmful-open"
    else:
        verdict = "no-harm-only"
    stalled = _stalled_ids(karte)
    clusters = _saturated_clusters(karte)
    findings = []
    for finding in karte.findings:
        related = karte.attempts_for_finding(finding.id)
        findings.append(
            {
                "id": finding.id,
                "status": finding.status,
                "harm": finding.harm,
                "harm_detail": finding.harm_detail,
                "locus": finding.locus,
                "summary": finding.summary,
                "rounds": list(finding.rounds),
                "resolved_round": finding.resolved_round,
                "attempts": [
                    {
                        "attempt": item.number,
                        "round": item.round,
                        "root_cause": item.root_cause,
                        "change_kind": item.change_kind,
                        "targets": list(item.targets),
                        "results": [
                            {
                                "outcome": result.outcome,
                                "touched": list(result.touched),
                                "note": result.note,
                            }
                            for result in karte.results_for(item.number)
                        ],
                    }
                    for item in related
                ],
            }
        )
    return {
        "issue": karte.issue,
        "verdict": verdict,
        "open_findings": [item.id for item in open_findings],
        "harmful_open": [item.id for item in harmful],
        "no_harm_open": [item.id for item in open_findings if item.harm == "none"],
        "stalled_findings": stalled,
        "stall_rounds": STALL_ROUNDS,
        "saturated_groups": clusters,
        "escalate": bool(stalled or clusters),
        "findings": findings,
    }


@_fail_close
def cmd_status(args) -> int:
    issue = _resolve_issue(args)
    _path, karte = _load(args, issue)
    payload = _status_payload(karte)
    if getattr(args, "json", False):
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return EXIT_OK

    verdict_label = {
        "clean": "clean（未解消の指摘なし）",
        "harmful-open": "harmful-open（実害あり残存）",
        "no-harm-only": "no-harm-only（全件実害なし）",
    }[payload["verdict"]]
    print(f"=== status: issue-{issue} ===")
    print(f"  verdict: {verdict_label}")
    print(f"  未解消: {', '.join(payload['open_findings']) or '(なし)'}")
    print(f"  実害あり: {', '.join(payload['harmful_open']) or '(なし)'}")
    print(f"  実害なし: {', '.join(payload['no_harm_open']) or '(なし)'}")
    print(
        f"  無進捗（{STALL_ROUNDS} ラウンド連続未解消）: "
        f"{', '.join(payload['stalled_findings']) or '(なし)'}"
    )
    if payload["saturated_groups"]:
        groups = "; ".join(
            "Attempt " + ", ".join(str(number) for number in members)
            for members in payload["saturated_groups"]
        )
        print(f"  類似グループ飽和: {groups}")
    print(f"  escalate: {'yes' if payload['escalate'] else 'no'}")
    for finding in payload["findings"]:
        if finding["status"] != "open":
            continue
        trace = []
        for attempt in finding["attempts"]:
            outcomes = ", ".join(result["outcome"] for result in attempt["results"]) or "未クローズ"
            trace.append(f"Attempt {attempt['attempt']}({attempt['root_cause']}→{outcomes})")
        print(f"  - {finding['id']}: {finding['summary']}")
        print(f"      診断/処置: {'; '.join(trace) or '(未診断)'}")
    return EXIT_OK


# --- パーサ ------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="karte",
        description="是正ループの診断カルテ（tmp/_karte/issue-<N>.md）を操作する",
    )
    subparsers = parser.add_subparsers(dest="verb", required=True)

    def add_issue(sub):
        sub.add_argument("--issue", help="Issue 番号（省略時は tmp/_karte/active.json）")

    ingest = subparsers.add_parser("ingest-review", help="レビューレポートを台帳へ取り込む")
    add_issue(ingest)
    ingest.add_argument("--round", required=True, help="レビューのラウンド番号（単調増加）")
    ingest.add_argument("--from", dest="source", required=True, help="レビューレポートのパス")
    ingest.set_defaults(func=cmd_ingest_review)

    render = subparsers.add_parser("render", help="Prior attempts と未解消 finding を出力")
    add_issue(render)
    render.set_defaults(func=cmd_render)

    append = subparsers.add_parser("append", help="Attempt を追記（類似飽和なら拒否）")
    add_issue(append)
    append.add_argument("--round", help="ラウンド番号（省略時は進行ポインタ）")
    append.add_argument("--finding-ids", nargs="+", required=True, help="対象の finding ID")
    append.add_argument("--root-cause", required=True, help="根本原因仮説の slug")
    append.add_argument(
        "--change-kind", required=True, choices=list(model.CHANGE_KINDS), help="変更の種類"
    )
    append.add_argument("--targets", nargs="+", required=True, help="触る関数/クラス（file::symbol）")
    append.add_argument("--diagnosis", default="", help="診断の要約（1行）")
    append.set_defaults(func=cmd_append)

    close = subparsers.add_parser("close-attempt", help="実測 touched-set を Result として追記")
    add_issue(close)
    close.add_argument("--attempt", help="対象 Attempt 番号（省略時は最新）")
    close.add_argument(
        "--outcome", required=True, choices=list(model.OUTCOMES), help="処置結果"
    )
    close.add_argument("--finding-ids", nargs="+", help="省略時は Attempt の finding_ids")
    close.add_argument("--base", default="HEAD", help="git diff の比較先（既定 HEAD）")
    close.add_argument("--diff-file", help="git を呼ばず既存の diff ファイルから算出する")
    close.add_argument("--note", default="", help="結果の補足（1行）")
    close.set_defaults(func=cmd_close_attempt)

    check = subparsers.add_parser("check", help="当該ラウンドの診断網羅を検査")
    add_issue(check)
    check.add_argument("--round", required=True, help="検査対象のラウンド番号")
    check.set_defaults(func=cmd_check)

    status = subparsers.add_parser("status", help="エスカレーション条件を機械判定")
    add_issue(status)
    status.add_argument("--json", action="store_true", help="機械可読な JSON で出力")
    status.set_defaults(func=cmd_status)
    return parser


def main(argv=None) -> int:
    """薄いディスパッチャ。終了コードへの変換は各 ``cmd_*``（:func:`_fail_close`）が担う。"""
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)
