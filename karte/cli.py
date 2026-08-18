"""karte の verb 実装（``python3 -m karte <verb>``・標準ライブラリのみ）。

verb:
  ``ingest-review``  レビューレポートを ``## Findings`` へ取り込む（ID 重複・未知 ID・
                     harm 欄欠落・同一指摘への ID 再発番・前ラウンド未解消の不在を検証）。
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
  ``check``          当該ラウンドの Attempt が存在し未解消 finding を網羅しているか、
                     および**全 Attempt** が ``close-attempt`` 済みか（実測信号の供給）。
  ``status``         実害あり残存 / 全件実害なし / 無進捗（同一 finding が3ラウンド連続未解消）
                     を機械判定する（エスカレーション条件）。既定出力は**そのまま注入できる
                     自己完結した本文**（K-15：PostToolUse フックが ``pr-reviewer`` 呼び出し
                     完了直後に実行してコンテキストへ注入する。ただし PostToolUse は
                     ツール呼び出しをブロックできず「判定を可視化する」までが役割）。

終了コード（``dsv2`` に合わせる）:
  0 OK ／ 2 未検出 ／ 3 類似飽和（append 拒否）／ 4 前提違反・検証失敗（fail-close）。

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
  **``append`` の ``--round`` 補完だけは例外**：ポインタが無い、または ``issue`` が
  対象と食い違う場合は fail-close せず、**カルテ内の最大ラウンドへ黙って縮退する**
  （ポインタが JSON として壊れている場合のみ :func:`_read_active` が拒否する）。
  ``append`` は停止ゲートではないため縮退しても安全——ラウンドのズレが起きても、
  **全 Attempt のクローズを要求する ``check`` が fail-close で必ず捕捉する**（K-02）ので、
  ここで厳格化しても二重の安全網にしかならない。

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

# `karte` パッケージが置かれているディレクトリ（＝repo-root の候補）。
_PACKAGE_ROOT = Path(__file__).resolve().parent.parent

# repo-root のオーバーライド点。**既定は None（＝未解決）**で、実際の導出は
# `_repo_root` が呼ばれたときに行う（K-12 の遅延評価）。
_REPO_ROOT = None


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
    """repo-root を **呼び出しごとに遅延解決**する（K-12）。

    linked worktree（``issue-implementer`` 等の isolated worktree）でも main worktree の
    ``tmp/_karte/`` へ収束させる（K-01）。``.git`` がファイルなら ``gitdir:`` を辿る
    :func:`paths.main_worktree_root` を使う（ガードは downstream の ``_resolved_root`` 等で
    必ず掛かる）。

    **import 時に評価しない**。``main_worktree_root`` は ``.git`` ファイルが不正形式なら
    :class:`KartePathError` を送出するが、モジュールレベルで評価すると、その例外は
    どの ``cmd_*``（:func:`_fail_close` でラップ済み）の内側でもない **import 時**に飛ぶ。
    結果、``.git`` が壊れた worktree では ``python3 -m karte <任意の verb>`` が未捕捉例外で
    終了し、文書化された終了コード ``{0,2,3,4}`` の外に漏れていた（K-03 と同種＝観測不能）。
    ここで解決すれば、経路が ``main()`` でも ``cmd_*`` 直呼びでも必ず ``_fail_close`` の
    内側に入る＝「ガードの効力を呼び出し経路に依存させない」規律と一貫する。

    結果をキャッシュしない（呼び出しごとに数回の ``.git`` 参照で済み、キャッシュすると
    プロセス内で worktree を跨ぐテスト・フックの挙動が呼び出し順に依存するため）。
    """
    override = getattr(args, "repo_root", None)
    if override:
        return Path(override).resolve()
    if _REPO_ROOT is not None:
        return Path(_REPO_ROOT)
    return paths.main_worktree_root(_PACKAGE_ROOT)


def _read_active(repo_root, *, required: bool = False) -> dict:
    """進行ポインタ ``tmp/_karte/active.json`` を読む。

    ``required``
        ``--issue`` / ``--round`` の補完に使う（＝これが唯一の情報源）とき True。
        ポインタが**まだ無い**場合に ``{}`` を返さず :class:`KarteUsageError` を送出する。

    **壊れている場合は ``required`` によらず常に拒否する**（K-13/K-14/K-15）。JSON として
    読めない・dict でないポインタを黙って「無い」と同じ ``{}`` に潰すと、補完が沈黙の
    うちに別の値（別 Issue・別ラウンド）へ倒れ、誤った台帳を書き換えても観測できない。
    「まだ無い」（正常な初期状態）と「壊れている」（異常）は別物として扱う。
    """
    try:
        path = paths.active_path(repo_root)
    except paths.KarteMissing as exc:
        if required:
            raise KarteUsageError(f"進行ポインタが無い: {exc}") from None
        return {}
    if not path.is_file():
        if required:
            raise KarteUsageError(
                f"進行ポインタ {path} が無い"
                "（先に `ingest-review --issue N --round R` を明示指定で実行する）"
            )
        return {}
    try:
        data = json.loads(paths.read_text(path))
    except ValueError as exc:
        raise KarteUsageError(
            f"進行ポインタ {path} が JSON として壊れている: {exc}"
            "（補完に使えないため取り込まない。ポインタを作り直すこと）"
        ) from None
    if not isinstance(data, dict):
        raise KarteUsageError(
            f"進行ポインタ {path} の中身が JSON オブジェクトでない: {type(data).__name__}"
        )
    return data


def _write_active(repo_root, issue: int, round_no: int) -> None:
    path = paths.active_path(repo_root, create_dir=True)
    paths.write_text_atomic(
        path, json.dumps({"issue": int(issue), "round": int(round_no)}, ensure_ascii=False) + "\n"
    )


def _resolve_issue(args) -> int:
    """``--issue`` 省略時は進行ポインタ ``tmp/_karte/active.json`` から補完する。

    フック（SubagentStart の ``render`` / SubagentStop の ``ingest-review`` / ``check`` /
    PostToolUse の ``status``）は dispatch prompt を読めないため、Issue 番号の唯一の情報源が
    このポインタになる（K-13/K-14/K-15）。
    ポインタが無い・壊れている・``issue`` を欠くときは推測せず fail-close する。
    """
    if getattr(args, "issue", None) is not None:
        return paths.validate_issue(args.issue)
    active = _read_active(_repo_root(args), required=True)
    if "issue" not in active:
        raise KarteUsageError(
            "--issue が未指定で、進行ポインタ tmp/_karte/active.json に 'issue' が無い"
            "（先に `ingest-review --issue N --round R` を実行する）"
        )
    return paths.validate_issue(active["issue"])


def _validate_round(value) -> int:
    text = str(value)
    if not text.isdigit() or int(text) < 1:
        raise KarteUsageError(f"round は 1 以上の整数: {value!r}")
    return int(text)


STDIN_SOURCE = "-"  # `--from -`＝標準入力（K-13・慣行に合わせる）


def _resolve_ingest_round(args, issue: int) -> int:
    """``ingest-review`` のラウンド番号を決める（``--round`` 省略時は進行ポインタ＋1）。

    ポインタが保持しているのは**最後に取り込んだ**ラウンド番号なので、新しいレビュー
    レポートは必ずその次のラウンドになる（同じ番号で再取り込みすると単調増加の検査に
    掛かって台帳の状態遷移が壊れる）。フックは「何ラウンド目か」を知る術がないため、
    ここで決定論的に導出する（K-13）。

    ポインタが無い・壊れている・``round`` を欠く・``issue`` が対象と食い違う場合は
    推測せず fail-close する（初回の取り込みは ``--issue``/``--round`` を明示して行う）。
    """
    if getattr(args, "round", None) is not None:
        return _validate_round(args.round)
    active = _read_active(_repo_root(args), required=True)
    if "round" not in active:
        raise KarteUsageError(
            "--round が未指定で、進行ポインタ tmp/_karte/active.json に 'round' も無い"
            "（初回の取り込みは `--round 1` を明示する）"
        )
    if "issue" in active and paths.validate_issue(active["issue"]) != issue:
        raise KarteUsageError(
            f"進行ポインタが指す issue-{active['issue']} と対象 issue-{issue} が食い違う"
            "（--round を明示するか、対象 Issue の取り込みからやり直す）"
        )
    return _validate_round(active["round"]) + 1


def _resolve_check_round(args, issue: int) -> int:
    """``check`` のラウンド番号を決める（``--round`` 省略時は進行ポインタの値を**そのまま**）。

    ``ingest-review`` と違って **+1 しない**——ポインタが保持しているのは「最後に取り込んだ
    ラウンド」で、``check`` が検査したいのはまさにそのラウンド（いま是正中のラウンド）だから。
    K-02 で ``check`` は SubagentStop フックの判定根拠になったが、**フックは dispatch prompt を
    読めない**ため、ここで補完できないとフック側がラウンド導出を再実装することになる
    （他 4 verb は補完できるのに ``check`` だけ非対称だった）。

    ポインタが無い・壊れている・``round`` を欠く・``issue`` が対象と食い違う場合は推測せず
    fail-close する（``_resolve_ingest_round`` と同じ扱い）。
    """
    if getattr(args, "round", None) is not None:
        return _validate_round(args.round)
    active = _read_active(_repo_root(args), required=True)
    if "round" not in active:
        raise KarteUsageError(
            "--round が未指定で、進行ポインタ tmp/_karte/active.json に 'round' も無い"
            "（`--round` を明示するか、先に `ingest-review` を実行する）"
        )
    if "issue" in active and paths.validate_issue(active["issue"]) != issue:
        raise KarteUsageError(
            f"進行ポインタが指す issue-{active['issue']} と対象 issue-{issue} が食い違う"
            "（--round を明示するか、対象 Issue の取り込みからやり直す）"
        )
    return _validate_round(active["round"])


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
    text = sys.stdin.read()
    if not text.strip():
        raise KarteUsageError(
            "`--from -` の標準入力が空（レビューレポート本文が渡されていない）。"
            "空入力を『指摘なし』とは解釈しない"
        )
    return text


def _validate_attempt_number(value) -> int:
    """``--attempt`` を検証する（``_validate_round`` と同型・K-03）。

    ``int(args.attempt)`` を無検証で呼ぶと非数値入力で ``ValueError`` が送出され、
    ``_fail_close`` の捕捉対象外（文書化された終了コード ``{0,2,3,4}`` の外）に漏れる。
    """
    text = str(value)
    if not text.isdigit() or int(text) < 1:
        raise KarteUsageError(f"attempt は 1 以上の整数: {value!r}")
    return int(text)


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
        return _validate_attempt_number(args.attempt)
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


def _saturated_groups(karte: model.Karte) -> list:
    """「同種の再試行がもう ``append`` できない」アプローチを列挙する（K-09：判定の一本化）。

    **``append`` のゲートとまったく同じ判定関数を使う**（:func:`similarity.find_hits` ＋
    :func:`similarity.is_saturated`）。違うのは主語だけで、``append`` の主語が「これから
    書き込もうとしている 1 件」であるのに対し、ここでは「**既に書かれた Attempt k と
    同じ宣言（root_cause / change_kind / targets）を繰り返す仮想の新規試行**」を主語に
    置く。したがって表示の意味は 1 つに定まる——

        ここに挙がったアプローチと**同種**の ``append`` は必ず ``EXIT_SATURATED`` になる。

    是正前は表示側だけが :func:`similarity.cluster`（union-find の連結成分）を使っており、
    推移律で広がるクラスタとゲートの pairwise 件数が食い違っていた。例えば
    A1(rc=x, logic, T1) と A2(rc=x, logic, T2) は change_kind 経由で 1 つの連結成分になる
    一方、A3(rc=x, interface, T2) は A2 とのみ類似（hits=1）なので ``append`` は通る
    ——「``render`` が飽和と言った直後に ``append`` が成功する」＝後工程が誤読した（K-09）。
    現在はどちらも同じ pairwise 判定なので、A1/A2 と同種の再試行だけが拒否対象として
    表示され、A3 のような別アプローチは表示にも現れないし拒否もされない。

    仮想の新規試行には実測 ``touched`` を持たせない（``append`` は修正の**前**に走るため
    新規側に実測値は存在しない）。比較相手の過去 Attempt 側には ``close-attempt`` で
    取り込んだ実測値を載せる——ここも ``append`` と同じ扱い。

    **比較相手（priors）も ``append`` と同じ集合にする**——すなわち候補ごとに
    :func:`_priors_for` で「その候補が対象とする**未解消** finding を共有する Attempt」へ
    絞る。以前はここだけが「未解消 finding をどれか共有する全 Attempt」を priors に使って
    おり、判定関数が 1 つでも**入力集合が 2 通り**あったため表示とゲートが再び食い違った：
    未解消 finding が 2 件あり Attempt を finding ごとに分けると、finding B の Attempt は
    finding A の Attempt 群まで priors に数えられて**飽和表示されるのに ``append`` は通る**
    （過大報告）。逆向き（``append`` は拒否するのに表示に出ない＝過少報告）も同じ穴の裏側。
    判定関数だけでなく**入力も一本化**して初めて K-09 の「表示＝ゲート」が成立する。

    戻り値は ``(candidate_number, members, hits, candidate_view)`` の列。
    ``members`` は「その再試行が衝突する Attempt 番号」（自分自身を含む）で、同じ
    ``members`` を持つ候補は先に現れた 1 件に畳む（同一グループを重複表示しない）。
    """
    open_ids = _open_ids(karte)
    relevant = [
        attempt for attempt in karte.attempts if open_ids & set(attempt.finding_ids)
    ]
    groups: list = []
    seen: set = set()
    for attempt in relevant:
        candidate = similarity.AttemptView(
            number=attempt.number,
            root_cause=attempt.root_cause,
            change_kind=attempt.change_kind,
            targets=tuple(attempt.targets),
            touched=(),
        )
        # `append` と同じ入力集合（候補の finding_ids でスコープした priors）を使う。
        priors = _priors_for(karte, attempt.finding_ids)
        hits = similarity.find_hits(candidate, priors)
        if not similarity.is_saturated(hits):
            continue
        members = tuple(sorted({hit.prior for hit in hits}))
        if members in seen:
            continue
        seen.add(members)
        groups.append((attempt.number, list(members), hits, candidate))
    return groups


def _group_directive(karte: model.Karte, candidate_number: int, hits, candidate) -> str:
    """飽和したアプローチの転換指令（``render`` / ``close-attempt`` の表示用）。"""
    attempt = karte.attempt(candidate_number)
    open_ids = _open_ids(karte) & set(attempt.finding_ids if attempt else [])
    return similarity.build_directive(
        candidate, hits, open_ids, subject_label="飽和したアプローチ"
    ).text()


# --- verb: ingest-review ------------------------------------------------------


@_fail_close
def cmd_ingest_review(args) -> int:
    """レビューレポートを台帳へ取り込む（検証に 1 件でも掛かれば**一切書かない**）。

    入力は ``--from <path>``（repo-root 配下）か ``--from -``（標準入力・K-13）。
    ``--issue`` / ``--round`` は進行ポインタから補完できる（:func:`_resolve_issue` /
    :func:`_resolve_ingest_round`）。検証は経路によらず共通で、ID 重複・未知 ID・
    harm 欄欠落・ID 再発番（K-05 の ``distinct_from`` で名指ししたペアだけ除外）・
    **前ラウンド未解消 finding の不在**（K-06）を見る。
    """
    repo_root = _repo_root(args)
    issue = _resolve_issue(args)
    round_no = _resolve_ingest_round(args, issue)
    report_text = _read_report(args, repo_root)

    path = paths.karte_path(issue, repo_root, create_dir=True)
    karte = model.parse(paths.read_text(path)) if path.is_file() else model.new_karte(issue)

    last_round = max((r for item in karte.findings for r in item.rounds), default=0)
    if round_no <= last_round:
        raise KarteUsageError(
            f"round は単調増加させる（取り込み済みの最新ラウンドは {last_round}・"
            f"指定は {round_no}）。同じラウンドの再取り込みは台帳の状態遷移を壊す"
        )

    review = model.parse_review(report_text, issue)
    previously_open = _open_ids(karte)

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

        bad_refs = _invalid_distinct_refs(karte, seen, finding_id, item)
        if bad_refs:
            errors.extend(bad_refs)
            continue

        if is_new:
            duplicate = _find_duplicate(karte, accepted, item)
            if duplicate is not None:
                errors.append(
                    f"{item.lineno} 行目: ID 再発番を検出: {finding_id} は既存の未解消 "
                    f"{duplicate} と同一の指摘（locus が交差し summary が一致）。"
                    "未解消の指摘を再度挙げるときは同じ ID を再利用すること"
                    f"（別物なら当該ブロックに `distinct_from: {duplicate}` を書いて名指しする）"
                )
                continue
        accepted.append((finding_id, item, is_new))

    # K-06: 「不在＝解消」を廃止する。前ラウンド時点で未解消だった finding が 1 件でも
    # 欠けていれば取り込みごと拒否する（部分的なレポート 1 通で `harm: real` の指摘が
    # 消える fail-open だった）。欠けている ID は全て列挙する（1 件ずつ往復させない）。
    absent = sorted(
        previously_open - {fid for fid, _item, _is_new in accepted},
        key=lambda fid: model.parse_finding_id(fid)[1],
    )
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

    created = []
    resolved = []
    excluded = []  # distinct_from で重複判定を外したペア（監査用に出力へ残す）
    for finding_id, item, _is_new in accepted:
        finding = karte.finding(finding_id)
        if finding is None:
            finding = model.Finding(id=finding_id)
            karte.findings.append(finding)
            created.append(finding_id)
        # K-06: 解消は**明示宣言**でのみ成立する（`harm` の値によらず一律）。
        finding.status = item.status
        finding.resolved_round = round_no if item.status == "resolved" else None
        if item.status == "resolved":
            resolved.append(finding_id)
        finding.harm = item.harm
        finding.harm_detail = item.harm_detail
        finding.severity = item.severity
        finding.locus = list(item.locus)
        finding.summary = item.summary
        finding.evidence = item.evidence
        finding.expected = item.expected
        finding.recheck = item.recheck
        if round_no not in finding.rounds:
            finding.rounds.append(round_no)
        finding.rounds.sort()
        for other in item.distinct_from:
            excluded.append(f"{finding_id} ↔ {other}")

    karte.findings.sort(key=lambda item: item.seq)
    paths.write_text_atomic(path, model.dumps(karte))
    _write_active(repo_root, issue, round_no)

    print(f"=== ingest-review: issue-{issue} round {round_no} ===")
    print(f"  取り込み: {len(accepted)} 件（新規 {len(created)} / 再掲 {len(accepted) - len(created)}）")
    if created:
        print(f"  新規採番: {', '.join(created)}")
    if resolved:
        print(f"  解消（レポートで `status: resolved` と明示された）: {', '.join(sorted(resolved))}")
    if excluded:
        print(f"  重複判定の明示的除外（distinct_from）: {'; '.join(excluded)}")
    print(f"  未解消: {', '.join(sorted(_open_ids(karte))) or '(なし)'}")
    print(f"  カルテ: {path}")
    return EXIT_OK


def _invalid_distinct_refs(karte: model.Karte, seen: set, finding_id: str, item) -> list:
    """``distinct_from`` の参照先が実在するか（K-05 のエスケープハッチを監査可能に保つ）。

    名指しできるのは **台帳にある finding** か、**同じレポート内で先に現れた finding** だけ。
    実在しない ID を書けてしまうと「何と別物か」の名指しが検証されず、重複判定を
    無効化するだけの呪文になる（＝握りつぶしの経路になる）ので fail-close で拒否する。
    自分自身の名指しも、判定を外す相手が存在しない無意味な宣言なので拒否する。
    """
    errors = []
    for other in item.distinct_from:
        if other == finding_id:
            errors.append(
                f"{item.lineno} 行目: distinct_from に自分自身は書けない: {other}"
            )
        elif karte.finding(other) is None and other not in seen:
            errors.append(
                f"{item.lineno} 行目: distinct_from が指す finding ID が実在しない: {other}"
                "（台帳にあるか、同じレポートで先に現れた ID だけを名指しできる）"
            )
    return errors


def _find_duplicate(karte: model.Karte, accepted, item):
    """新規採番しようとしている指摘が、既存の未解消 finding の焼き直しでないかを見る。

    ``item.distinct_from`` で名指しされた相手は比較から外す（K-05）。外れるのは
    **名指しされたペアだけ**で、判定そのもの・閾値
    （:data:`model.DUPLICATE_SIMILARITY_THRESHOLD`）は据え置く——偽陽性の逃げ道として
    閾値を下げると、本来検出したい再発番まで一律に見逃す。
    """
    exempt = set(item.distinct_from)
    for finding in karte.open_findings():
        if finding.id in exempt:
            continue
        if model.is_same_finding(item.summary, item.locus, finding.summary, finding.locus):
            return finding.id
    for finding_id, other, _is_new in accepted:
        if finding_id in exempt:
            continue
        if model.is_same_finding(item.summary, item.locus, other.summary, other.locus):
            return finding_id
    return None


# --- verb: render -------------------------------------------------------------


@_fail_close
def cmd_render(args) -> int:
    """カルテの現在状態を**そのまま注入できる本文**として出力する（K-14）。

    SubagentStart フック（matcher ``issue-fixer``）がこれを実行し、標準出力を
    ``hookSpecificOutput.additionalContext`` として是正エージェントへ自動注入する。
    「是正エージェントに ``render`` を引かせる」設計だと、呼び忘れたら過去の試行を
    知らないまま修正に入る——本件（同じ失敗の繰り返し）で直そうとしている失敗そのものが
    残るため、注入側に寄せた。

    したがって出力は**自己完結**させる:
      * 何の本文か・受け手が何をすべきかを冒頭で述べる（前後の文脈に依存しない）。
      * 過去 Attempt 一覧（実測 touched と Result を含む）／未解消 finding 一覧／
        飽和したアプローチの転換指令を、この 1 通で完結させる。
      * 端末装飾（色・カーソル制御）や対話前提の文言（「上記の…」「続けますか」）を混ぜない。

    ``--issue`` は進行ポインタから補完できる（フックは dispatch prompt を読めない）。
    カルテ未作成は :data:`EXIT_NOT_FOUND` のまま（ガード違反＝EXIT_ERROR と区別する）。
    """
    issue = _resolve_issue(args)
    path, karte = _load(args, issue)
    active = _read_active(_repo_root(args))
    round_no = active.get("round") if active.get("issue") == issue else None

    lines = [f"=== Karte: issue-{issue}" + (f" / round {round_no}" if round_no else "") + " ==="]
    lines.append(
        f"これは Issue #{issue} の是正ループの診断カルテ（{path}）から機械生成した現在状態である。"
    )
    lines.append(
        "同じ失敗を繰り返さないために、以下の Prior attempts と同じ診断・同じ変更箇所を"
        "もう一度なぞらないこと。新しい試行は着手前に "
        f"`python3 -m karte append --issue {issue} --finding-ids <ID...> --root-cause <slug> "
        "--change-kind <kind> --targets <file::symbol...>` で宣言し、修正後に "
        f"`python3 -m karte close-attempt --issue {issue} --outcome <fixed|partial|no-change|regressed>` "
        "で実測差分を記録すること（記録しないと `check` が通らず停止できない）。"
    )
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
            f"  - {finding.id} [harm={finding.harm}] [severity={finding.severity}] "
            f"rounds={finding.rounds}{stalled}"
        )
        lines.append(f"      summary: {finding.summary}")
        lines.append(f"      harm_detail: {finding.harm_detail}")
        if finding.locus:
            lines.append(f"      locus: {', '.join(finding.locus)}")
        lines.append(f"      evidence: {finding.evidence}")
        # expected / recheck は是正側の入力契約そのもの（Issue #341 F-341-01）。
        # ここに出さないと `issue-fixer` は「何をもって解消か」を前ラウンドから引けない。
        lines.append(f"      expected: {finding.expected}")
        lines.append(f"      recheck: {finding.recheck}")
        related = karte.attempts_for_finding(finding.id)
        if related:
            lines.append(
                "      対応した Attempt: "
                + ", ".join(str(item.number) for item in related)
            )

    groups = _saturated_groups(karte)
    if groups:
        lines.append("")
        lines.append("## 飽和したアプローチ（同種の再試行は append が拒否される）")
        lines.append(
            "  以下と**同種**の Attempt（root_cause が同じで change_kind が同じか targets が"
            "重なるもの、あるいは実測 touched-set が一致するもの）を append すると "
            "EXIT_SATURATED で拒否され、カルテには書かれない。"
        )
        lines.append(
            "  ここに挙がっていないアプローチ（root_cause と targets を変えたもの）の append は"
            "拒否されない——この節は「次の append が必ず落ちる」という意味ではなく、"
            "「**このアプローチを繰り返す** append が落ちる」という意味である。"
        )
        for number, members, hits, candidate in groups:
            lines.append(
                f"  - Attempt {number} と同種（root_cause={candidate.root_cause} / "
                f"change_kind={candidate.change_kind} / "
                f"targets={', '.join(candidate.targets)}）: "
                f"衝突する既存 Attempt {', '.join(str(item) for item in members)}"
            )
            directive = _group_directive(karte, number, hits, candidate)
            if directive:
                lines.append(directive)

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
        diff_path = paths.resolve_within_repo(args.diff_file, _repo_root(args))
        diff_text = paths.read_text(diff_path)
    else:
        diff_text = touched_mod.git_diff(_repo_root(args), args.base)
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


@_fail_close
def cmd_check(args) -> int:
    """当該ラウンドの診断網羅と、**全 Attempt のクローズ**を検査する。

    合格条件は 2 つ:
      1. 当該ラウンドの Attempt が未解消 finding を網羅している。
      2. **カルテ上の全 Attempt** が ``close-attempt`` 済み（Result を持つ）。

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

    ``--round`` は進行ポインタから補完できる（:func:`_resolve_check_round`）。フックは
    dispatch prompt を読めないので、ここが必須だとフック側でラウンド導出を再実装させる。
    """
    issue = _resolve_issue(args)
    _path, karte = _load(args, issue)
    round_no = _resolve_check_round(args, issue)

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
    # K-09: 表示（ここ）とゲート（append）は同じ判定関数を使う。`saturated_groups` は
    # 「そのアプローチを繰り返す append が拒否される」既存 Attempt の組。
    saturated = [members for _number, members, _hits, _candidate in _saturated_groups(karte)]
    findings = []
    for finding in karte.findings:
        related = karte.attempts_for_finding(finding.id)
        findings.append(
            {
                "id": finding.id,
                "status": finding.status,
                "harm": finding.harm,
                "harm_detail": finding.harm_detail,
                "severity": finding.severity,
                "locus": list(finding.locus),
                "summary": finding.summary,
                "evidence": finding.evidence,
                "expected": finding.expected,
                "recheck": finding.recheck,
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
        "saturated_groups": saturated,
        "escalate": bool(stalled or saturated),
        "findings": findings,
    }


@_fail_close
def cmd_status(args) -> int:
    """エスカレーション条件を機械判定し、**そのまま注入できる本文**として出力する（K-15）。

    PostToolUse フック（matcher ``Task``）が ``pr-reviewer`` 呼び出し完了直後にこれを実行し、
    判定結果をコンテキストへ自動注入する。**PostToolUse はツール呼び出しをブロックできない**
    （公式ドキュメント：the tool already ran／blocking does not undo the tool call）ため、
    この verb の役割は「判定を必ず実行し可視化する」までであり、「判定に反した行動
    （実害あり残存のまま merge する等）を止める」のは別途 PreToolUse で merge 操作を
    捕まえるゲートが担う（Issue #293／#298・本 verb の対象外）。

    ``--issue`` は進行ポインタ（``tmp/_karte/active.json``）から補完できる（K-13/K-14 と
    同じ扱い）。既定出力（非 ``--json``）は残存 finding とその harm 判定・verdict・
    エスカレーション条件のどれに該当するかを 1 通で完結させる（端末装飾・対話前提の
    文言は混ぜない）。機械可読が要るときは ``--json`` を使う（挙動は変えない）。
    """
    issue = _resolve_issue(args)
    path, karte = _load(args, issue)
    payload = _status_payload(karte)
    if getattr(args, "json", False):
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return EXIT_OK

    verdict_label = {
        "clean": "clean（未解消の指摘なし）",
        "harmful-open": "harmful-open（実害あり残存）",
        "no-harm-only": "no-harm-only（全件実害なし）",
    }[payload["verdict"]]
    lines = [f"=== status: issue-{issue} ==="]
    lines.append(
        f"これは Issue #{issue} の是正ループの進捗判定を、診断カルテ（{path}）から"
        "機械生成した現在状態である（karte status）。"
    )
    lines.append(f"  verdict: {verdict_label}")
    lines.append(f"  未解消: {', '.join(payload['open_findings']) or '(なし)'}")
    lines.append(f"  実害あり: {', '.join(payload['harmful_open']) or '(なし)'}")
    lines.append(f"  実害なし: {', '.join(payload['no_harm_open']) or '(なし)'}")
    lines.append(
        f"  無進捗（{STALL_ROUNDS} ラウンド連続未解消）: "
        f"{', '.join(payload['stalled_findings']) or '(なし)'}"
    )
    if payload["saturated_groups"]:
        groups = "; ".join(
            "Attempt " + ", ".join(str(number) for number in members)
            for members in payload["saturated_groups"]
        )
        # K-09: 「同種の再試行が拒否される組」であって「次の append が必ず落ちる」ではない。
        lines.append(
            f"  飽和したアプローチ（同種の再試行は append が拒否される）: {groups}"
        )
    if payload["escalate"]:
        reasons = []
        if payload["stalled_findings"]:
            reasons.append(f"無進捗（{', '.join(payload['stalled_findings'])}）")
        if payload["saturated_groups"]:
            reasons.append("飽和したアプローチあり")
        lines.append(f"  escalate: yes（理由: {' / '.join(reasons) or '不明'}）")
    else:
        lines.append("  escalate: no（無進捗・飽和したアプローチのいずれにも該当しない）")
    lines.append("")
    lines.append("## 残存 finding（未解消・harm 判定つき）")
    open_lines = [item for item in payload["findings"] if item["status"] == "open"]
    if not open_lines:
        lines.append("  (未解消の指摘なし)")
    for finding in open_lines:
        trace = []
        for attempt in finding["attempts"]:
            outcomes = ", ".join(result["outcome"] for result in attempt["results"]) or "未クローズ"
            trace.append(f"Attempt {attempt['attempt']}({attempt['root_cause']}→{outcomes})")
        lines.append(f"  - {finding['id']} [harm={finding['harm']}]: {finding['summary']}")
        lines.append(f"      診断/処置: {'; '.join(trace) or '(未診断)'}")
    print("\n".join(lines))
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
    return parser


def main(argv=None) -> int:
    """薄いディスパッチャ。終了コードへの変換は各 ``cmd_*``（:func:`_fail_close`）が担う。"""
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)
