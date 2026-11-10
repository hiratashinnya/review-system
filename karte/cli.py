"""karte の verb 実装（``python3 -m karte <verb>``・標準ライブラリのみ）。

verb:
  ``ingest-review``  レビューレポートを ``## Findings`` へ取り込む（ID 重複・未知 ID・
                     harm/scope 欄欠落・**``harm_detail`` への処置方針/経緯の混入**
                     （Issue #511・:func:`karte.model.check_harm_detail`）・
                     disposition の不整合・同一指摘への ID 再発番・
                     前ラウンド未解消の不在を検証）。``## Findings`` は**スコープの内外を
                     問わない単一の列**で、``issue-implementer``/``issue-fixer`` の
                     ハンドオフ ``out_of_scope_findings`` も同じ書式へ写してここへ取り込む
                     （取り込みの実行は主文脈・Issue #495）。
                     ``--from -`` で **stdin** からも読める（K-13：SubagentStop フックが
                     ``last_assistant_message`` を直接食わせるため、人手の中継を挟まない）。
  ``render``         「Prior attempts（DO NOT repeat these）」＋未解消 finding 一覧。
                     同種の再試行が拒否される段階に達したアプローチは転換指令も合成する。
                     出力は **subagent のコンテキストへそのまま注入できる自己完結した本文**
                     （K-14：SubagentStart フックが ``additionalContext`` として注入する）。
  ``append``         Attempt をスキーマ検証つきで追記。類似飽和なら**書き込まず**拒否し、
                     反復された root_cause / targets を名指しした転換指令を stdout に返す。
  ``close-attempt``  修正後の実測 touched-set を ``### Result k`` として追記する
                     （実測信号の供給源。Attempt ブロック自体は書き換えない）。
                     ``--attempt`` 省略時は未クローズの Attempt が1つならそれを使い、
                     2つ以上あれば fail-close して明示を要求する（Issue #378・詳細は
                     :func:`_resolve_close_attempt_number`）。実測 diff が空のときは
                     ``--outcome no-change`` の場合を除き fail-close する（Issue #355・
                     詳細は README）。宣言 ``targets`` と実測 touched が一切重ならない
                     ときは警告のみ（拒否はしない・Issue #378 C）。
  ``check``          当該ラウンドの Attempt が存在し**診断が要る**未解消 finding を
                     網羅しているか、および**全 Attempt** が ``close-attempt`` 済みか
                     （実測信号の供給）。``disposition: deferred``/``waived``＝「当該 PR では
                     処置しない」と決まった finding は診断網羅の要求から外す（Issue #503
                     観測1。外す前は毎ラウンド必ず 1 回 block し、停止ゲートが形骸化した）。
  ``status``         実害あり残存 / 全件実害なし / 無進捗（同一 finding が3ラウンド連続未解消）
                     を機械判定する（エスカレーション条件）。**``clean`` は「未解消 0 件」では
                     なく「clean を妨げる未解消 0 件」**＝``harm: real`` で
                     ``disposition`` 未決定の finding が1件でも残る間は ``clean`` を返さない
                     （``scope: out`` でも免除しない）。``disposition: deferred``/``waived``
                     だけが ``status: open`` のまま verdict を妨げなくなる（Issue #495）。
                     無進捗判定も同じ除外を受ける（Issue #503 観測3。誰も直さないと決めた
                     finding に進捗が無いのは当然で、拾うと ``escalate`` が偽陽性になる）。
                     既定出力は**そのまま注入できる
                     自己完結した本文**（人手／フックのどちらから呼んでも常に全件出力する。
                     K-15 が構想した「PostToolUse フックが ``pr-reviewer`` 呼び出し完了直後に
                     コンテキストへ注入する」自動可視化は未配線のまま、Issue #512 が対応する
                     AC を移譲し**別の設計**で実装した——届け先を AI のコンテキスト
                     （``additionalContext``）ではなく**オーナーのチャット**（``systemMessage``）
                     にし、``ingest-review`` / ``ingest-reviewer`` / ``decide`` / ``close-attempt`` や
                     Codex reviewer wrapper の実行を検出する（実体は :mod:`karte_notify`・
                     ``.claude/hooks/karte-notify.sh``）。理由は、AI のコンテキストへ注入する
                     だけでは「機械判定が AI の要約を経て歪む」経路（実例＝PR #509／Issue #431：
                     ``escalate: yes`` を主文脈が独自解釈して丸めた）を防げないため。この
                     verb 自身（``status``）は変更していない——``karte_notify`` は本 verb の
                     ``--json`` 出力を読むだけの外部消費者であり、finding ID 単位の既読管理は
                     ``karte_notify`` 側の責務。ただし PostToolUse はツール呼び出しをブロック
                     できず「判定を可視化する」までが役割である点は変わらない）。

終了コード（``dsv2`` に合わせる）:
  0 OK ／ 2 未検出 ／ 3 類似飽和（append 拒否）／ 4 前提違反・検証失敗（fail-close）。
  5 取り込み済み・未完了（EXIT_INCOMPLETE・レビューアの再掲漏れ。台帳は書込み済みで失敗ではない）。
  読み込む入力（レポート本文のファイル・標準入力、台帳、進行ポインタ、``--diff-file``）が UTF-8 として
  読めないときも 4（traceback の終了コード 1 にしない・Issue #696 F-696-13）。

進行ポインタ（``tmp/_karte/active.json``）による補完:
  フック（SubagentStart / SubagentStop）は dispatch prompt を読めないため、Issue 番号と
  ラウンド番号の唯一の情報源が進行ポインタになる。``--issue`` は全 verb で、``--round`` は
  ``ingest-review`` / ``append`` / ``check`` で省略でき、省略時はポインタから補完する。
  補完する値は verb で違う——``ingest-review`` は「最後に取り込んだラウンド **＋1**」
  （新しいレビューは必ず次のラウンド）、``append`` / ``check`` は「最後に取り込んだ
  ラウンド **そのまま**」（いま是正中のラウンドを対象にする）。
  **``ingest-review`` / ``check`` はポインタが無い・壊れている・必要なキーを欠く場合は
  補完せず EXIT_ERROR**（fail-close）——壊れたポインタを「無い」と同じに扱うと、
  別 Issue の台帳へ黙って書きかねない。
  **``append`` の ``--round`` 補完だけは例外**（:func:`karte.pointer_completion.recorded_round`）：ポインタが無い・
  ``issue`` が対象と食い違う（キー欠落・型違いを含む）・``round`` が 0/欠落（偽値）なら、fail-close せず
  **カルテ内の最大ラウンドへ黙って縮退する**。拒否するのは、ポインタが壊れている／オブジェクトでない場合
  （:func:`karte.active_pointer.read_active`）と、``round`` が偽値でないのに型違い・非 ASCII 数字・巨大桁・負・NaN・
  bool の場合（:func:`karte.int_args.parse_int`）で、どちらも終了コード 4。縮退しても**全 Attempt のクローズを
  要求する ``check`` が必ず捕捉する**（K-02）。``render`` の見出しの ``round`` も同じ読み方で、無効値は 4。
  補完の実装は :mod:`karte.pointer_completion`。``ingest-review`` は、引数・ポインタ・本文由来の
  拒否を issue→round→本文の順にロックの**前**で行い（何も作らない）、ポインタ由来の値だけは
  ロックの内側で読み直す（:func:`_prepare_ingest`）。

``repo_root`` は **公開 CLI フラグとしては持たない**内部専用パラメータ
（``args`` に属性として渡されたときだけ使う）。実運用は常にリポジトリルートで動くため、
公開フラグは信頼境界を広げるだけの攻撃面になる（``dsv2/cli.py`` の
``cmd_clean_tmp`` と同じ判断・issue #276 round-2）。テストは ``argparse.Namespace`` を
直接組み立てて各 ``cmd_*`` を呼ぶ。

依存仕様: :mod:`karte` の docstring（Issue #307）。
"""

from __future__ import annotations

import argparse
import json
import sys

from . import (
    active_pointer,
    ingest_review,
    int_args,
    karte_loader,
    model,
    paths,
    pointer_completion,
    repo_roots,
    similarity,
)
from . import touched as touched_mod
from .errors import KarteUsageError
from .exit_codes import EXIT_ERROR, EXIT_OK, EXIT_SATURATED
from .render_text import render_lines
from .saturation_groups import group_directive as _group_directive
from .saturation_groups import priors_for as _priors_for
from .saturation_groups import saturated_groups as _saturated_groups
from .stall_detection import STALL_ROUNDS as STALL_ROUNDS
from .stall_detection import stalled_ids as _stalled_ids
from .status_payload import status_payload as _status_payload
from .status_text import status_lines
from .utf8_text import read_stream_text
from .verb_boundary import fail_close, require_declared

STDIN_SOURCE = "-"  # `--from -`＝標準入力（K-13・慣行に合わせる）


# --- 共通ヘルパ --------------------------------------------------------------


def _read_report(args, repo_root) -> str:
    """レビューレポート本文を ``--from`` から読む（``-`` は標準入力）。

    stdin 経路は K-13（SubagentStop フックが ``last_assistant_message`` をそのまま
    パイプする）のために設ける。**検証は経路によらず同一**——本文を得たあとの処理は
    ファイル経路と 1 本の流れに合流するので、ID 重複・未知 ID・harm 欄欠落・
    K-06 の不在禁止・K-05 の ``distinct_from`` はどちらでも同じように効く。

    空入力は「指摘なし」と解釈しない（fail-close）。フックが本文を渡し損ねた場合と
    「レビューの結果ゼロ件だった」場合を区別できず、後者を装って台帳の未解消指摘を
    素通しできてしまうため（K-06 と同じ fail-open の型）。
    """
    source = getattr(args, "source", None)
    if source is None:
        raise KarteUsageError("--from が未指定（レポートのパスか `-`（標準入力）を指定する）")
    if str(source) != STDIN_SOURCE:
        return paths.read_text(paths.resolve_within_repo(source, repo_root))
    if sys.stdin is None:
        raise KarteUsageError("`--from -` が指定されたが標準入力が無い")
    text = read_stream_text(sys.stdin)
    if not text.strip():
        raise KarteUsageError(
            "`--from -` の標準入力が空（レビューレポート本文が渡されていない）。"
            "空入力を『指摘なし』とは解釈しない"
        )
    return text


def _resolve_close_attempt_number(args, karte) -> int:
    """``close-attempt`` の ``--attempt`` 省略時の既定値を決める（Issue #378・案 B）。

    以前は「直近で append された Attempt」（``next_attempt_number() - 1``）へ無条件に
    解決していた。複数 Attempt を先に append してからまとめて close する運用では、
    **最後に append した Attempt へ全部が吸い込まれ**、誤った Attempt への記録を
    2 ラウンド連続で誘発した（PR #364 是正ラウンド 2・3）。

    新しい規則:
      * 未クローズ（``results_for`` が空）の Attempt が **ちょうど 1 つ**なら、それを使う
        （最新でなくてもよい——曖昧さが無いので安全側）。これが「1 つ append → すぐ close」
        という従来からの主要な運用と一致し、後方互換を保つ。
      * 未クローズが **複数** あれば、どれを閉じるつもりか読み取れないので fail-close し、
        ``--attempt`` の明示を要求する（曖昧なら止めるのが最も確実・B の哲学）。
      * 未クローズが **0** なら、fail-close して ``--attempt`` の明示か ``append`` を促す。
        ただし「0」は 2 通りの事実を含みうるので、それぞれ**自分の状態を正しく述べる**
        メッセージに分ける（F-378-01）——
          - **Attempt が 1 件も無い**（``append`` をまだ 1 度も呼んでいない）。
          - **Attempt はあるが全件クローズ済み**（結果は既に記録されている）。
        両者を同じ「全 Attempt が既にクローズ済み」文言に潰すと、Attempt を1件も
        append していない利用者に事実と異なる説明を返す（実行時挙動＝fail-close は
        どちらも正しいが、原因の説明が不正確になる）。
    """
    if args.attempt is not None:
        return int_args.parse_int(args.attempt, "attempt")
    unclosed = [item.number for item in karte.attempts if not karte.results_for(item.number)]
    if len(unclosed) > 1:
        raise KarteUsageError(
            "--attempt が未指定で、未クローズの Attempt が複数ある（"
            + ", ".join(f"Attempt {number}" for number in unclosed)
            + "）。どの Attempt に記録するか --attempt で明示すること（Issue #378）"
        )
    if len(unclosed) == 1:
        return unclosed[0]
    if not karte.attempts:
        raise KarteUsageError(
            "--attempt が未指定で、カルテに Attempt が1件も無い。"
            "先に `append` すること（Issue #378）"
        )
    raise KarteUsageError(
        "--attempt が未指定で、全 Attempt が既にクローズ済み。"
        "--attempt を明示するか、先に `append` すること（Issue #378）"
    )


# --- verb: ingest-review ------------------------------------------------------


def _prepare_ingest(args, repo_root) -> str:
    """ロック前の段。``--issue``→``--round``→本文の順に検証し、拒否なら何も作らず本文を返す。

    補完結果はここでは捨てる（ポインタ由来の値は、ロック内で読み直した値だけが正）。
    """
    pointer_completion.ingest_target(args, repo_root)
    return _read_report(args, repo_root)


@fail_close(locked=True, prepare=_prepare_ingest)
def cmd_ingest_review(args, repo_root, report_text) -> int:
    """レビューレポートを台帳へ取り込む（検証に 1 件でも掛かれば台帳・ポインタを**一切書かない**）。

    入力は ``--from <path>``（repo-root 配下）か ``--from -``（標準入力・K-13）。ロックの**前**
    （``prepare``）で ``--issue``→``--round``→本文の順に検証して本文を読む——引数・ポインタ・本文
    由来の拒否は ``tmp/_karte/`` も作らず、閉じない標準入力でロックを握り続けることもない。
    ``--issue`` / ``--round`` はポインタから補完でき、**補完は最終的にロックの内側で読み直す**
    （外の値は信用しない。並行 ingest が同じ次ラウンドを選ぶため）。何も作らずに拒否できるのは ``prepare`` 段で拒否できる範囲に限る。
    ロック内の拒否（競合でのポインタ変化・内容検証・台帳との突き合わせ）は新規 repo でも ``tmp/_karte/`` と ``.writer.lock`` を残す（台帳・ポインタは書かない）。検証は経路によらず共通で、ID 重複・
    未知 ID・harm 欄欠落・**``scope`` 欄欠落**（Issue #495）・**``disposition`` の不整合**
    （``deferred`` に ``deferred_to`` が無い等）・ID 再発番（K-05 の ``distinct_from`` で名指し
    したペアだけ除外）・**前ラウンド未解消 finding の不在**（K-06）を見る。
    """
    issue, round_no = pointer_completion.ingest_target(args, repo_root)
    return ingest_review.ingest_locked(repo_root, issue, round_no, report_text)


# --- verb: render -------------------------------------------------------------


@fail_close(locked=False)
def cmd_render(args, repo_root) -> int:
    """カルテの現在状態を本文として出力する。"""
    issue = pointer_completion.resolve_issue(args, repo_root)
    path, karte = karte_loader.load_karte(repo_root, issue)
    active = active_pointer.read_active(repo_root)
    round_no = pointer_completion.recorded_round(active, issue)
    print("\n".join(render_lines(issue, path, round_no, karte)))
    return EXIT_OK


# --- verb: append -------------------------------------------------------------


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


# --- verb: close-attempt ------------------------------------------------------


@fail_close(locked=True)
def cmd_close_attempt(args, repo_root) -> int:
    issue = pointer_completion.resolve_issue(args, repo_root)
    path, karte = karte_loader.load_karte(repo_root, issue)
    number = _resolve_close_attempt_number(args, karte)
    attempt = karte.attempt(number)
    if attempt is None:
        raise KarteUsageError(f"Attempt {number} がカルテに無い（先に `append` する）")
    if karte.results_for(number):
        raise KarteUsageError(
            f"Attempt {number} には既に Result がある（既存ブロックは書き換えない＝追記のみ）"
        )

    outcome = _validate_outcome(args.outcome)

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

    print(f"=== close-attempt: issue-{issue} Attempt {number} ===")
    print(f"  outcome: {result.outcome}")
    print(f"  実測 touched: {', '.join(result.touched) or '(差分なし・no-change)'}")

    target_files = {item.split("::", 1)[0] for item in attempt.targets}
    touched_files = {item.split("::", 1)[0] for item in measured}
    if measured and not (target_files & touched_files):
        print(
            "  注意: 宣言 targets（"
            + ", ".join(attempt.targets)
            + "）と実測 touched（"
            + ", ".join(measured)
            + "）が重ならない。誤った Attempt に記録した可能性がある"
            "（Issue #378 C）"
        )

    karte = model.parse(paths.read_text(path))
    for candidate_number, members, hits, candidate in _saturated_groups(karte):
        if number not in members:
            continue
        print("")
        print(
            f"  注意: Attempt {candidate_number} と同種のアプローチは飽和した"
            f"（衝突する既存 Attempt {', '.join(str(item) for item in members)}）。"
            "同種の append は拒否される"
        )
        print(_group_directive(karte, candidate_number, hits, candidate))
    print(f"  カルテ: {path}")
    return EXIT_OK


def _validate_outcome(value: str) -> str:
    text = model.check_scalar(value, "outcome")
    if text not in model.OUTCOMES:
        raise KarteUsageError(f"outcome は {list(model.OUTCOMES)} のいずれか: {value!r}")
    return text


# --- verb: check --------------------------------------------------------------


@fail_close(locked=False)
def cmd_check(args, repo_root) -> int:
    """当該ラウンドの診断網羅と、**全 Attempt のクローズ**を検査する。

    合格条件は 2 つ:
      1. 当該ラウンドの Attempt が、**この PR で是正が求められている**未解消 finding
         （:meth:`model.Karte.remediation_findings`）を網羅している。
      2. **カルテ上の全 Attempt** が ``close-attempt`` 済み（Result を持つ）。

    1 の対象から ``disposition: deferred``/``waived`` を除くのが Issue #503 の是正
    （観測1）。除外前は「直さないと決まった finding」にも診断を要求していたため、
    是正担当が指示どおりそれを触らずに他を完璧に是正しても ``check`` が必ず
    ``EXIT_ERROR`` を返し、SubagentStop の停止ゲートが**毎ラウンド 1 回 block**した。
    診断を求めるべきなのは「これから直す finding」であって「直さないと決まった
    finding」ではない——後者に診断を書かせることは、`.claude/rules/03-operational.md`
    「スコープ拡大禁止」に反する記録を台帳へ入れさせることでもある。**除外規則は
    ``status`` の verdict・無進捗検知と同じ単一の述語**（``needs_remediation``）を
    使う（判定経路ごとに実装しない）。

    2 を課すのが K-02 の是正。実測 touched-set の唯一の供給源は ``close-attempt`` だが、
    以前は ``check`` も ``append`` も「直前の Attempt がクローズ済みであること」を求めて
    いなかった。そのため ``root_cause`` を毎回書き換えるだけの試行は、``close-attempt`` を
    一度も呼ばなければ宣言信号にも実測信号（測定値ゼロ）にも掛からず**無制限に通った**
    ——偽装ではなく**呼び忘れだけ**でゲートが無効化できた。``check`` は SubagentStop
    フックの判定根拠なので、ここで落とせば「クローズしないと前に進めない」になる。

    2 の対象を「当該ラウンド**以前**」ではなく**全 Attempt** にするのは逃げ道を残さない
    ため。``append --round <大きい値>`` で先のラウンドを名乗った Attempt は、以前は
    ``round <= --round`` の絞り込みから外れて未クローズのまま ``check`` を通せた
    ——既定経路では踏まないとしても、「呼ばれないと進まないように作る」を掲げる以上
    暗黙の前提（＝呼び出し側がラウンドを正直に申告すること）に依存させない。

    ``--round`` は進行ポインタの値を**そのまま**補完できる（``ingest-review`` と違って +1 しない。
    検査したいのは最後に取り込んだ＝いま是正中のラウンド）。フックは dispatch prompt を
    読めないので、ここが必須だとフック側でラウンド導出を再実装させる（K-02）。
    """
    issue = pointer_completion.resolve_issue(args, repo_root)
    _path, karte = karte_loader.load_karte(repo_root, issue)
    round_no = pointer_completion.resolve_round(
        args, repo_root, issue, pointer_completion.MissingRoundHint.RUN_INGEST_FIRST
    ).number

    attempts = [item for item in karte.attempts if item.round == round_no]
    expected = sorted(
        item.id for item in karte.remediation_findings() if round_no in item.rounds
    )
    # Issue #503: 除外した finding は黙って落とさず必ず見せる（何を診断しなくてよいのか、
    # なぜそう判定したのかを読み手が台帳を開かずに確認できるようにする）。
    excused = sorted(
        f"{item.id}（{item.disposition}）"
        for item in karte.open_findings()
        if item.cleared_by_disposition and round_no in item.rounds
    )
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
    if excused:
        print(
            "  診断不要（disposition で当該 PR では処置しないと決定済み・status は open のまま）: "
            + ", ".join(excused)
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


# --- verb: status -------------------------------------------------------------


@fail_close(locked=False)
def cmd_status(args, repo_root) -> int:
    """進捗判定を本文または JSON として出力する。"""
    issue = pointer_completion.resolve_issue(args, repo_root)
    path, karte = karte_loader.load_karte(repo_root, issue)
    payload = _status_payload(karte)
    if getattr(args, "json", False):
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return EXIT_OK
    print("\n".join(status_lines(issue, path, payload)))
    return EXIT_OK


# --- パーサ ------------------------------------------------------------------


def build_parser(extra_registrars=()) -> argparse.ArgumentParser:
    """``extra_registrars``＝``(subparsers, add_issue)`` を受けて verb を足す関数の列（別モジュールの verb 用）。

    登録 verb は ``func`` を ``fail_close(locked=...)`` で包んでロック要否を宣言しなければならない。
    宣言の無い verb があれば :class:`ValueError` で組み立てを拒否する（fail-close）。
    """
    parser = argparse.ArgumentParser(
        prog="karte",
        description="是正ループの診断カルテ（tmp/_karte/issue-<N>.md）を操作する",
    )
    subparsers = parser.add_subparsers(dest="verb", required=True)

    def add_issue(sub):
        sub.add_argument("--issue", help="Issue 番号（省略時は tmp/_karte/active.json）")

    ingest = subparsers.add_parser("ingest-review", help="レビューレポートを台帳へ取り込む")
    add_issue(ingest)
    ingest.add_argument(
        "--round",
        help="レビューのラウンド番号（単調増加。省略時は tmp/_karte/active.json の次のラウンド）",
    )
    ingest.add_argument(
        "--from",
        dest="source",
        required=True,
        help=f"レビューレポートのパス（`{STDIN_SOURCE}` で標準入力から読む）",
    )
    ingest.set_defaults(func=cmd_ingest_review)

    render = subparsers.add_parser(
        "render", help="Prior attempts と未解消 finding を注入用の本文として出力"
    )
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
    close.add_argument(
        "--attempt",
        help=(
            "対象 Attempt 番号（省略時: 未クローズの Attempt が1つならそれを使う。"
            "2つ以上あれば曖昧なので明示を要求して拒否する。0（Attempt が1件も無い、"
            "または全件クローズ済み）でも同様に明示を要求して拒否する＝Issue #378）"
        ),
    )
    close.add_argument(
        "--outcome", required=True, choices=list(model.OUTCOMES), help="処置結果"
    )
    close.add_argument("--finding-ids", nargs="+", help="省略時は Attempt の finding_ids")
    close.add_argument(
        "--base",
        default="HEAD",
        help=(
            "git diff の比較先（既定 HEAD）。commit・push 後は作業ツリーが HEAD と一致し"
            "diff が空になる——その場合は変更前の commit（例 HEAD~1）を明示するか"
            "--diff-file を使う。診断せず空 diff で fixed/partial 等を記録することは"
            "できない（--outcome no-change の場合のみ例外＝Issue #355）"
        ),
    )
    close.add_argument("--diff-file", help="git を呼ばず既存の diff ファイルから算出する")
    close.add_argument("--note", default="", help="結果の補足（1行）")
    close.set_defaults(func=cmd_close_attempt)

    check = subparsers.add_parser("check", help="当該ラウンドの診断網羅を検査")
    add_issue(check)
    check.add_argument(
        "--round",
        help="検査対象のラウンド番号（省略時は tmp/_karte/active.json の round をそのまま使う）",
    )
    check.set_defaults(func=cmd_check)

    status = subparsers.add_parser("status", help="エスカレーション条件を機械判定")
    add_issue(status)
    status.add_argument("--json", action="store_true", help="機械可読な JSON で出力")
    status.set_defaults(func=cmd_status)
    for register in extra_registrars:
        register(subparsers, add_issue)
    require_declared(subparsers)
    return parser


def main(argv=None, extra_registrars=()) -> int:
    """薄いディスパッチャ。終了コードへの変換とロックは各 verb 自身の宣言
    （:func:`karte.verb_boundary.fail_close`）が担い、ここでは再ラップしない。"""
    args = build_parser(extra_registrars).parse_args(argv)
    return args.func(args)
