"""``SubagentStart`` / ``SubagentStop`` フックの実体（Issue #309・PR-1）。

3つの verb を1モジュールに束ねる（``.claude/hooks/*.sh`` はそれぞれ薄い起動口）:

===================  =====================  ==========================================
verb                 イベント / matcher     役割
===================  =====================  ==========================================
``karte-inject``     SubagentStart          ``issue-fixer`` へカルテ手順＋
                     ``issue-fixer``        ``karte render`` の出力を
                                            ``additionalContext`` として注入する（助言）
``bind``             SubagentStart          起動した dispatch の worktree を所有台帳へ
                     implementer / fixer    束縛する（``open`` → ``running``）
``stop``             SubagentStop           カルテ未更新のまま停止させない（block）
                     implementer / fixer    ＋ **回収・解放段**（Issue #354・PR-3）
===================  =====================  ==========================================

**このモジュールは ``git worktree remove`` を直接呼ばない。** 解放は
``python3 -m gitgate collect-worktree``（回収→検証→解放の段構造・:mod:`gitgate.worktree`）を
起動する形だけで行う＝「回収せずに解放する」経路がフック側に**作りようがない**（FR-W2）。

「終了」と「一時停止」の区別（Issue #423）
----------------------------------------
``SubagentStop`` は**その dispatch が本当に終了したときだけ**発火するとは限らない。
``issue-implementer`` / ``issue-fixer`` 自身が入れ子の ``Task`` 委譲を行うと、同じ
``agent_id`` の停止イベントが委譲のたびに届く（Issue #338 実装中に実測）。台帳の状態と
payload だけでは両者を区別できないため、**区別は「自分の handoff が書けているか」という
観測可能な成果物**で行う（`.claude/rules/01-principles.md`「観測できないものは持たない」）。

* 自分の handoff が**1件ある** → 契約上の成果物が揃った＝**終了**。回収して解放する。
* 自分の handoff が**無い** → 終了したのか、まだ書く段に到達していない（入れ子委譲待ちで
  一時停止しただけ）のか決められない＝**保留**。台帳は ``running`` のまま何もしない。

保留を ``stopped`` / ``stale`` へ落とさないのが要点である。どちらも
:data:`issue_start.worktree_ledger.RESIDUE_STATUSES` に入るため、落とすと
``issue-start-gate`` の残留チェックが**同じ dispatch 自身の次の入れ子委譲**まで
``ISSUE_START_WORKTREE_RESIDUE`` で拒否してしまう（Issue #423 の実害そのもの）。

**したがって本モジュールは ``--allow-missing-handoff`` を組み立てない。**「回収するものが
無いことを列挙で確認した」という判断は、入れ子委譲待ちの一時停止と見分けがつかない以上、
フックが自動で下してよいものではない。``gitgate collect-worktree`` 側のこのフラグは残るが、
**主文脈が明示的に使う operator 用の逃げ道**であって自動経路ではない。

fail 方針の非対称（設計判断・``.claude/hooks/README.md`` にも明記）
------------------------------------------------------------------
* **停止のブロックは fail-close**：``issue-fixer`` のカルテ判定が**不能**なら block する
  （``active.json`` 欠如・破損・``karte check`` を起動できない、を含む）。
* **worktree の削除は fail-safe＝「消さない」側に倒す**：台帳を引けない・遷移できない・
  回収が失敗した・timeout した——どの経路でも削除せず ``stale`` へ落として返す。
* **「終了したか判らない」も fail-safe 側**：``stale`` にすら落とさず ``running`` を保つ
  （``stale`` は「回収を試みて失敗した」を意味する状態で、まだ試みていない保留とは違う）。
* 両者は**方向が逆**である。ブロックの誤りは「余計に止まる」だけで回復可能だが、削除の
  誤りは成果物を回復不能に失う。削除しなかったぶんの残留は次 dispatch の gate deny
  （``ISSUE_START_WORKTREE_RESIDUE``）が拾う。
* **「回収は済んだが削除だけ git ロックで失敗した」は保留 = ``release_pending``**（Issue #464）。
  ``collect-worktree`` が handoff を退避（``collected_to``）してから ``git worktree remove`` で
  詰まった場合、成果物は失われていないので ``stale`` へ落とさない。この停止イベントの時点では
  ロックはまだエージェントプロセスが握っているため、解放段はここで何もせず
  （``RELEASE_PENDING_DEFERRED``）、削除は次 dispatch の gate がロックの外れた後に引き取る。
* **解放段の失敗は停止をブロックしない**：block できるのはカルテ段だけで、解放段は evidence を
  残して exit 0 する。解放できないことを理由にエージェントを止め続けても解決しない（当人には
  ``gitgate`` の worktree verb が許可されていない）ので、制御を主文脈へ返して deny で気づかせる。

対象外ロールの扱い
------------------
``agent_type`` が対象外・欠落・payload が読めない場合は **常に無出力（stdout）exit 0**
（``agent-command-gate.sh`` の「対象外ロールは常に許可」不変条件と同型）。**この
in-script 判定があるので、要実測事項 V-2（``matcher`` が ``agent_type`` 名で効くか）の
結果がどちらでも契約は成立する**——matcher が効けば発火自体が絞られ、効かなければ
ここで無出力 exit 0 になる。

**ただし stderr には必ず evidence を1行書く**（F-309-05）。「発火しなかった」と
「発火したが対象外と判定した」は post-merge の実測（V-1 / V-2）で最も知りたい区別であり、
無出力 exit 0 のままでは両者が見分けられない。stdout（＝ハーネスへの契約面）は
無出力のまま、診断は stderr（``claude --debug``）へ寄せる。

依存仕様:
  * :mod:`issue_start.worktree_ledger`（台帳 API・状態遷移）
  * :mod:`gitgate.worktree` の ``collect-worktree``（受理する台帳 status・引数スキーマ）
  * ``karte`` CLI の ``check``（終了コード 0=OK / 2=未検出 / 4=前提違反）
  * ``karte/cli.py`` の進行ポインタ規約（``tmp/_karte/active.json`` の ``{issue, round}``）
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence, TextIO

from . import worktree_ledger

TARGET_ROLES = ("issue-implementer", "issue-fixer")
KARTE_ROLE = "issue-fixer"
KARTE_PROTOCOL_REL = ".claude/hooks/karte-protocol.md"
KARTE_CHECK_TIMEOUT_S = 30.0
KARTE_RENDER_TIMEOUT_S = 30.0
# 回収・解放段（`gitgate collect-worktree`）の上限。`settings.json` の
# `SubagentStop` timeout（60s）に収まる値にする——フック全体が打ち切られると
# 「回収したのに台帳へ書けていない」中途半端な状態になりうる。
COLLECT_TIMEOUT_S = 45.0
# 回収対象の handoff を探すディレクトリ（作業ツリールート相対）。
HANDOFF_DIR_REL = "tmp/_handoff"
# 「自分の handoff が無い」ことを台帳へ1度だけ書き残すときの marker（重複追記の抑止に使う）。
# 入れ子委譲を何段も行う dispatch では停止イベントが何度も届くため、毎回 notes を積むと
# 台帳が観測ログで埋まり、ロック取得回数も無駄に増える（Issue #423 の並列度の論点）。
HANDOFF_PENDING_MARKER = "HANDOFF_PENDING"
# 注入本文の区切り（手順書 → 過去の試行）。render 出力は自己完結した本文なので、
# 手順書とはっきり分けて末尾に置く（直近＝最も読まれる位置に「なぞるな」を置く）。
INJECT_SEPARATOR = "\n\n---\n\n"

# `issue_start/` の親＝リポジトリルート。フックの起動口が PYTHONPATH に
# `$CLAUDE_PROJECT_DIR` を入れるため、main worktree 側の実体がここに解決される。
PACKAGE_ROOT = Path(__file__).resolve().parent.parent


class ActivePointerError(Exception):
    """進行ポインタ ``tmp/_karte/active.json`` を一意に読めない（判定不能＝block）。"""


# --- payload -------------------------------------------------------------------


def load_payload(stdin: TextIO) -> dict | None:
    """stdin の JSON を読む。読めなければ ``None``（対象外扱い＝無出力 exit 0）。"""
    try:
        value = json.load(stdin)
    except (json.JSONDecodeError, UnicodeDecodeError, ValueError, OSError):
        return None
    return value if isinstance(value, dict) else None


def agent_type_of(payload: Mapping[str, Any] | None) -> str | None:
    """payload から ``agent_type`` を読む（読めなければ ``None``）。

    ``agent_type`` / ``subagent_type`` の両綴りを見る。``agent-command-gate.sh`` が
    PreToolUse payload で使う綴りは ``agent_type`` だが、``SubagentStart`` /
    ``SubagentStop`` payload の綴りは本 repo では未実測（要実測事項 V-2 の周辺）。
    **どちらでもない場合は推測せず ``None``**（＝対象外として無出力 exit 0）。
    """
    if not isinstance(payload, Mapping):
        return None
    for key in ("agent_type", "subagent_type"):
        value = payload.get(key)
        if isinstance(value, str) and value:
            return value
    return None


def agent_id_of(payload: Mapping[str, Any] | None) -> str | None:
    """payload から ``agent_id`` を読む（読めなければ ``None``）。

    ``None`` でも束縛は成立しうる（:func:`worktree_ledger.resolve_worktree_for_agent` の
    差分検出＝選択肢 BIND-1 案A）。
    """
    if not isinstance(payload, Mapping):
        return None
    for key in ("agent_id", "subagent_id"):
        value = payload.get(key)
        if isinstance(value, str) and value:
            return value
    return None


def _cwd_of(payload: Mapping[str, Any] | None, fallback: Path | None) -> Path:
    if fallback is not None:
        return Path(fallback)
    if isinstance(payload, Mapping):
        value = payload.get("cwd")
        if isinstance(value, str) and value:
            return Path(value)
    return Path.cwd()


def _evidence(stderr: TextIO, verb: str, **fields: Any) -> None:
    payload = {"hook": f"subagent-{verb}", **fields}
    stderr.write(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
    )


def _payload_keys(payload: Mapping[str, Any] | None) -> list | None:
    """観測した payload のキー集合（読めなければ ``None``）。

    値は載せない（dispatch prompt・パス等が stderr へ漏れる）。**キーの集合だけ**でも
    「payload は届いたが ``agent_type`` の綴りが違う」と「payload 自体が読めない」を
    区別できる＝要実測事項 V-2 の判定材料になる（F-309-05）。
    """
    if not isinstance(payload, Mapping):
        return None
    return sorted(str(key) for key in payload)


def _skip_evidence(
    stderr: TextIO, verb: str, payload: Mapping[str, Any] | None, agent_type: str | None
) -> int:
    """対象外・payload 不読の経路の evidence（stdout は無出力のまま exit 0）。"""
    _evidence(
        stderr, verb,
        result="skip",
        reason="PAYLOAD_UNREADABLE" if payload is None else "OUT_OF_SCOPE",
        agent_type=agent_type,
        payload_keys=_payload_keys(payload),
    )
    return 0


def _block(stdout: TextIO, reason: str) -> int:
    """``SubagentStop`` の停止拒否。**exit code は 0 のまま**（既存ハーネスの前提を壊さない）。"""
    json.dump({"decision": "block", "reason": reason}, stdout, ensure_ascii=False)
    stdout.write("\n")
    return 0


# --- verb: karte-inject（SubagentStart・matcher issue-fixer） --------------------


def karte_render_argv(issue: int) -> list:
    """``karte render`` の argv（``git worktree remove`` を含まないことを明示する境界）。"""
    return [sys.executable, "-m", "karte", "render", "--issue", str(issue)]


def _read_protocol(root: Path, stderr: TextIO) -> str:
    """注入する手順書本文（読めなければ空文字＝その節だけ落とす）。"""
    protocol = Path(root) / KARTE_PROTOCOL_REL
    try:
        body = protocol.read_text(encoding="utf-8").strip()
    except OSError as exc:
        _evidence(stderr, "karte-inject", result="protocol-skip", error=type(exc).__name__)
        return ""
    if not body:
        _evidence(stderr, "karte-inject", result="protocol-skip", error="EMPTY_PROTOCOL")
    return body


def _render_karte(
    stderr: TextIO,
    *,
    payload: Mapping[str, Any] | None,
    cwd: Path | None,
    runner: Callable[..., subprocess.CompletedProcess],
) -> str:
    """``python3 -m karte render --issue <N>`` の出力（取れなければ空文字＝fail-open）。

    ``{issue, round}`` の出所は進行ポインタ ``tmp/_karte/active.json`` だけ
    （``SubagentStart`` payload に dispatch prompt が無い）。**``--issue`` は必ず明示する**
    ——並行運用時に別 Issue の台帳を読ませない（``karte-protocol.md`` と同じ規律）。

    ここは**注入＝助言**なので全経路 fail-open（読めなければ黙って節を落とす）。
    停止ゲート側（:func:`run_stop`）の fail-close とは方向が逆であることに注意
    （注入の失敗は「知らずに直す」だけだが、停止の誤許可は統制の消失になる）。
    """
    try:
        repo_root = worktree_ledger.main_worktree_root(_cwd_of(payload, cwd))
    except Exception as exc:
        _evidence(
            stderr, "karte-inject", result="render-skip",
            reason="REPO_ROOT_UNRESOLVED", error=type(exc).__name__,
        )
        return ""
    try:
        issue, _round = read_active_pointer(repo_root)
    except ActivePointerError as exc:
        _evidence(
            stderr, "karte-inject", result="render-skip",
            reason="ACTIVE_POINTER_UNREADABLE", detail=str(exc),
        )
        return ""
    try:
        completed = runner(
            karte_render_argv(issue),
            cwd=str(repo_root),
            text=True,
            capture_output=True,
            shell=False,
            timeout=KARTE_RENDER_TIMEOUT_S,
        )
    except Exception as exc:
        _evidence(
            stderr, "karte-inject", result="render-skip",
            reason="KARTE_RENDER_UNRUNNABLE", error=type(exc).__name__, issue=issue,
        )
        return ""
    returncode = getattr(completed, "returncode", None)
    body = (getattr(completed, "stdout", "") or "").strip()
    if returncode != 0 or not body:
        _evidence(
            stderr, "karte-inject", result="render-skip",
            reason="KARTE_RENDER_FAILED", exit_code=returncode, issue=issue,
        )
        return ""
    _evidence(stderr, "karte-inject", result="render-ok", issue=issue, chars=len(body))
    return body


def run_karte_inject(
    *,
    stdin: TextIO,
    stdout: TextIO,
    stderr: TextIO,
    project_root: Path | None = None,
    cwd: Path | None = None,
    runner: Callable[..., subprocess.CompletedProcess] = subprocess.run,
) -> int:
    """カルテ手順＋``karte render`` の出力を ``additionalContext`` に注入する（助言＝fail-open）。

    **注入本文は2節**（この順に連結する）:

    1. **手順書**（``.claude/hooks/karte-protocol.md``）＝毎ラウンド同じ規範。シェルからも
       python からも分離しておくのは ``inject-governance.sh`` と同作法。
    2. **``karte render`` の出力**＝そのラウンド固有の状態（Prior attempts・未解消 finding・
       転換指令）。**K-14 の要求そのもの**——``karte/cli.py::cmd_render`` の docstring は
       「SubagentStart フックがこれを実行し標準出力を ``additionalContext`` として自動注入する」
       と定めている。是正エージェント自身に ``render`` を呼ばせる設計は「呼び忘れたら過去の
       試行を知らないまま修正に入る」ため**明示的に却下されている**ので、ここで実行する
       （F-309-04：手順書だけを注入していた実装を K-14 に合わせた）。

    2 を「手順書の指示に委ねる」形へ戻さないこと。手順書は 1 として残るが、それは
    **render を呼べ**という規範であって、**render の出力**の代わりにはならない。

    どちらの節も取れなければ何も注入せず exit 0（注入は助言＝fail-open）。
    """
    payload = load_payload(stdin)
    agent_type = agent_type_of(payload)
    if agent_type != KARTE_ROLE:
        return _skip_evidence(stderr, "karte-inject", payload, agent_type)
    root = PACKAGE_ROOT if project_root is None else Path(project_root)
    sections = [
        section
        for section in (
            _read_protocol(root, stderr),
            _render_karte(stderr, payload=payload, cwd=cwd, runner=runner),
        )
        if section
    ]
    if not sections:
        _evidence(stderr, "karte-inject", result="skip", reason="NOTHING_TO_INJECT")
        return 0
    json.dump(
        {
            "hookSpecificOutput": {
                "hookEventName": "SubagentStart",
                "additionalContext": INJECT_SEPARATOR.join(sections),
            }
        },
        stdout,
        ensure_ascii=False,
    )
    stdout.write("\n")
    return 0


# --- verb: bind（SubagentStart・matcher issue-implementer|issue-fixer） ----------


def run_bind(
    *,
    stdin: TextIO,
    stdout: TextIO,
    stderr: TextIO,
    cwd: Path | None = None,
    now: datetime | None = None,
) -> int:
    """起動した dispatch の worktree を所有台帳へ束縛する（``open`` → ``running``）。

    **出力は常に無出力 exit 0**（本 PR では何も止めない）。evidence は stderr。
    worktree を一意に決められないときは**束縛せず**、該当 ``open`` エントリに
    ``notes`` を1行足すだけにする（推測して別の dispatch のエントリを潰さない）。
    """
    payload = load_payload(stdin)
    agent_type = agent_type_of(payload)
    if agent_type not in TARGET_ROLES:
        return _skip_evidence(stderr, "bind", payload, agent_type)
    stamp = datetime.now(timezone.utc) if now is None else now
    agent_id = agent_id_of(payload)
    try:
        repo_root = worktree_ledger.main_worktree_root(_cwd_of(payload, cwd))
        worktree_path, how = worktree_ledger.resolve_worktree_for_agent(
            repo_root, agent_id=agent_id
        )
        if worktree_path is None:
            entry = worktree_ledger.latest_open_entry(repo_root, agent_type)
            if entry is not None:
                worktree_ledger.add_note(
                    repo_root,
                    entry["entry_id"],
                    now=stamp,
                    note=f"SubagentStart で worktree を一意に決められず束縛しなかった（{how}）",
                )
            _evidence(
                stderr, "bind", result="unbound", how=how,
                agent_type=agent_type, agent_id=agent_id,
                entry_id=None if entry is None else entry["entry_id"],
            )
            return 0
        # 束縛キーは payload の `agent_id` を優先する（`SubagentStop` が同じキーで引くため）。
        # payload に無い／台帳が受け付けない形の場合だけ、差分検出で決まった worktree の
        # ディレクトリ名から復元する（推測ではなく実在するディレクトリ名が根拠）。
        directory_id = worktree_path.rsplit("/agent-", 1)[-1]
        bind_key = (
            agent_id
            if agent_id and worktree_ledger.AGENT_ID_RE.fullmatch(agent_id)
            else directory_id
        )
        entry_id = worktree_ledger.bind_agent(
            repo_root,
            agent_type=agent_type,
            agent_id=bind_key,
            worktree_path=worktree_path,
        )
        _evidence(
            stderr, "bind",
            result="bound" if entry_id else "no-open-entry",
            how=how, agent_type=agent_type, agent_id=agent_id,
            worktree_path=worktree_path, entry_id=entry_id,
        )
    except worktree_ledger.LedgerError as exc:
        _evidence(stderr, "bind", result="error", reason=exc.reason, detail=exc.detail)
    except Exception as exc:  # 台帳の事故で dispatch を巻き込まない（本 PR は fail-open）
        _evidence(stderr, "bind", result="error", reason=type(exc).__name__)
    return 0


# --- verb: stop（SubagentStop・matcher issue-implementer|issue-fixer） -----------


def read_active_pointer(repo_root: Path) -> tuple:
    """``tmp/_karte/active.json`` から ``(issue, round)`` を読む。

    読めない・壊れている・キーを欠く・型が不正なら :class:`ActivePointerError`
    （＝判定不能なので呼び出し側は block する＝fail-close）。
    """
    tmp = Path(repo_root) / "tmp"
    if tmp.is_symlink():
        raise ActivePointerError(f"tmp が symlink: {tmp}")
    directory = tmp / "_karte"
    if directory.is_symlink():
        raise ActivePointerError(f"カルテ置き場が symlink: {directory}")
    path = directory / "active.json"
    if path.is_symlink():
        raise ActivePointerError(f"進行ポインタが symlink: {path}")
    if not path.is_file():
        raise ActivePointerError(f"進行ポインタが無い: {path}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ActivePointerError(f"進行ポインタを読めない/JSON が壊れている: {path}（{exc}）")
    if not isinstance(value, dict):
        raise ActivePointerError(f"進行ポインタが JSON オブジェクトでない: {path}")
    issue, round_no = value.get("issue"), value.get("round")
    for name, item in (("issue", issue), ("round", round_no)):
        if not isinstance(item, int) or isinstance(item, bool) or item < 1:
            raise ActivePointerError(
                f"進行ポインタの '{name}' が 1 以上の整数でない: {path}（{item!r}）"
            )
    return issue, round_no


def karte_check_argv(issue: int, round_no: int) -> list:
    """``karte check`` の argv（``git worktree remove`` を含まないことを明示する境界）。"""
    return [
        sys.executable, "-m", "karte", "check",
        "--issue", str(issue), "--round", str(round_no),
    ]


def is_reentrant_stop(payload: Mapping[str, Any] | None) -> bool:
    """**この停止ゲートで一度 block した結果の再入**か（``stop_hook_active``）。

    ``SubagentStop`` payload の ``stop_hook_active`` は「フックが停止を拒否したため
    エージェントが継続している」ことを表す。2回目以降は**判定を繰り返さず通す**
    （F-309-02）。

    なぜ必要か: fail-close の block reason が指す脱出手順は、条件によっては
    **ブロックされた当人には実行できない**（進行ポインタの再生成に要る
    ``karte ingest-review`` は是正当事者に許されない＝Issue #308 / #341）。再入判定が
    無いと、当人が満たしようのない条件を突きつけられたまま永久に停止できない。
    「1回は必ず止めて理由を届ける／2回目は通す」にすることで、fail-close の目的
    （見落としの防止）を保ったまま無限ループを**構造的に**断つ。

    ゲートを弱めないための前提: 1回目の block は必ず発生し、reason は
    :func:`_remediation` / :func:`_pointer_remediation` としてエージェントへ届く。
    握り潰しではなく「同じ判定の繰り返しをやめる」だけである。
    """
    if not isinstance(payload, Mapping):
        return False
    for key in ("stop_hook_active", "subagent_stop_hook_active"):
        if payload.get(key) is True:
            return True
    return False


def _pointer_remediation(detail: str) -> str:
    """``{issue, round}`` を確定できないときの reason（当人が実行できる手順だけを書く）。"""
    return (
        f"issue-fixer の停止を拒否する（Issue #309・判定不能は fail-close）: {detail}\n"
        "この拒否は**1回だけ**（次の停止要求は stop_hook_active により素通しする）。\n"
        "issue-fixer 自身が実行できる手順:\n"
        "  1. 今ラウンドの診断と実測をカルテへ記録する"
        "（python3 -m karte append … / python3 -m karte close-attempt …）。\n"
        "  2. 進行ポインタ tmp/_karte/active.json の再生成には karte ingest-review が要るが、"
        "**これは是正当事者には許されない**（Issue #308 / #341）。自分で作り直そうとせず、"
        "「進行ポインタが読めないので主文脈が ingest-review で作り直す必要がある」ことを"
        "ハンドオフの stop_reason に書いて、呼び出し元へ報告して停止すること。"
    )


def _remediation(issue: int, round_no: int, detail: str) -> str:
    return (
        f"issue-fixer の停止を拒否する（Issue #309）: {detail}\n"
        "着手した是正の診断がカルテに記録されていない。停止する前に次を実行すること:\n"
        f"  python3 -m karte render --issue {issue}\n"
        f"  python3 -m karte append --issue {issue} --round {round_no} "
        "--finding-ids <F-...> --root-cause <slug> --change-kind <kind> --targets <file::symbol...>\n"
        f"  python3 -m karte close-attempt --issue {issue} "
        "--outcome <fixed|partial|no-change|regressed>\n"
        f"  python3 -m karte check --issue {issue} --round {round_no}   # これが exit 0 になれば停止できる"
    )


def _karte_stop_gate(
    *,
    stdout: TextIO,
    stderr: TextIO,
    payload: Mapping[str, Any] | None,
    cwd: Path | None,
    runner: Callable[..., subprocess.CompletedProcess],
) -> int | None:
    """``issue-fixer`` のカルテ検査段。**block したら exit code、通してよければ ``None``**。

    呼び出し側（:func:`run_stop`）は ``None`` 以外が返ったらそこで打ち切る＝「block したら
    後段（PR-3 の解放段）へ進まない」を型で表す。
    """
    if is_reentrant_stop(payload):
        _evidence(stderr, "stop", result="allow", reason="STOP_HOOK_REENTRY")
        return None
    try:
        repo_root = worktree_ledger.main_worktree_root(_cwd_of(payload, cwd))
    except Exception as exc:  # 台帳/カルテの置き場が決まらない＝判定不能（fail-close）
        _evidence(
            stderr, "stop", result="block",
            reason="REPO_ROOT_UNRESOLVED", error=type(exc).__name__,
        )
        return _block(
            stdout,
            _pointer_remediation(
                f"カルテの置き場（main worktree root）を導出できない（{type(exc).__name__}: {exc}）"
            ),
        )
    try:
        issue, round_no = read_active_pointer(repo_root)
    except ActivePointerError as exc:
        _evidence(stderr, "stop", result="block", reason="ACTIVE_POINTER_UNREADABLE")
        return _block(stdout, _pointer_remediation(str(exc)))
    try:
        completed = runner(
            karte_check_argv(issue, round_no),
            cwd=str(repo_root),
            text=True,
            capture_output=True,
            shell=False,
            timeout=KARTE_CHECK_TIMEOUT_S,
        )
    except Exception as exc:  # 起動不能＝判定不能なので block（fail-close）
        _evidence(stderr, "stop", result="block", reason="KARTE_CHECK_UNRUNNABLE")
        return _block(
            stdout,
            _remediation(issue, round_no, f"`karte check` を起動できなかった（{type(exc).__name__}）"),
        )
    returncode = getattr(completed, "returncode", None)
    if returncode != 0:
        stderr_text = (getattr(completed, "stderr", "") or "").strip()
        _evidence(stderr, "stop", result="block", reason="KARTE_CHECK_FAILED", exit_code=returncode)
        return _block(
            stdout,
            _remediation(
                issue, round_no,
                f"`karte check --issue {issue} --round {round_no}` が exit {returncode}"
                + (f"\n{stderr_text}" if stderr_text else ""),
            ),
        )
    _evidence(stderr, "stop", result="allow", reason="KARTE_CHECK_OK", issue=issue, round=round_no)
    return None


def collect_worktree_argv(entry_id: str, *, handoff: str | None) -> list:
    """``gitgate collect-worktree`` の argv（**ここが唯一の解放経路**）。

    フックは ``git worktree remove`` を直接呼ばない——実体を消してよいかの判断
    （台帳の状態・パス形状・git 管理下かの検査・回収→検証→解放の段構造）はすべて
    :mod:`gitgate.worktree` に集約されており、フックはその verb を起動するだけにする。
    こうすると「回収せずに解放する」経路がフック側に**作りようがない**（FR-W2）。

    ``handoff`` の2形だけを組み立てる:

    * **パス** → ``--handoff <path>``。自分の handoff を1件に決められた＝回収して解放する。
    * ``None`` → ``--entry`` だけ。**既に ``collected`` のエントリを解放するだけ**の形で、
      ``gitgate`` 側は ``collected`` のとき回収段を丸ごと飛ばすので handoff 引数を見ない。

    **``--allow-missing-handoff`` は組み立てない**（Issue #423）。「回収するものが無い」は
    「まだ書いていない（入れ子委譲待ちで一時停止中）」と区別できないため、フックが自動で
    その判断を下す経路そのものを無くす。同フラグは ``gitgate`` 側に残るが、主文脈が明示的に
    使う operator 用の逃げ道である。
    """
    argv = [sys.executable, "-m", "gitgate", "collect-worktree", "--entry", entry_id]
    if handoff is not None:
        argv += ["--handoff", handoff]
    return argv


def own_handoff_pattern(agent_type: str, issue: int) -> re.Pattern:
    """**この dispatch 自身が書く** handoff のファイル名にだけ一致する正規表現。

    ``<agent_type>--issue-<N>[<境界><suffix>].yaml`` で、``issue-<N>`` の直後は ``-`` か
    ``.`` に限る（``issue-3541`` を ``issue-354`` と取り違えないための境界検査）。規則は
    ``gitgate/worktree.py`` の ``HANDOFF_FILENAME_RE`` および各 agent 契約の
    「``handoff_path`` の検査」条件4・5 と同一だが、**フックは ``gitgate`` を import しない**
    （起動するだけ）という境界を保つためここで独立に組み立てる。

    ``agent_type`` を名前に含めるのが要点である。入れ子委譲を行う dispatch では、委譲先
    （``verification-author`` / ``reconciliation`` 等）の handoff が**同じ**
    ``tmp/_handoff/`` に溜まる。所有者を見ずに数だけ数えると、他人の成果物1件を自分のものと
    誤認したり、2件以上で ``ambiguous`` に落ちて回収不能になったりする（Issue #423 の実測）。
    """
    return re.compile(
        rf"^{re.escape(agent_type)}--issue-{int(issue)}(-[A-Za-z0-9._-]*)?\.yaml$"
    )


def _discover_handoff(repo_root: Path, worktree_path: str, *, agent_type: str, issue) -> tuple:
    """dispatch の worktree から**自分の**回収対象 handoff を1つに決める。

    返り値は ``(relative_path | None, how)``。``how`` は evidence 用の識別子。

    現行の ``ISSUE_START_BINDING_V1`` marker には ``handoff_path`` が無く、台帳の
    ``handoff_path`` は ``None`` のまま起票される。そのため ``collect-worktree --entry <id>``
    だけでは回収元が決まらず ``COLLECT_HANDOFF_UNKNOWN`` で必ず落ちる。ここで**実在する
    ファイルを列挙して**決めることで、marker を触らずに回収を成立させる。

    判定は次のいずれかになる（推測しない）:

    * :func:`own_handoff_pattern` に一致するファイルが**ちょうど1件** → そのパス
      （``how="unique"``）。これが唯一の「終了した」signal である。
    * 一致が**0件** → ``(None, "empty")``。``tmp/_handoff`` 自体が無い場合も、他人
      （委譲先エージェント）の handoff だけがある場合も同じ扱いで、**「終了」とは言えない**。
      呼び出し側は解放も ``stale`` 化もせず ``running`` のまま保留する（Issue #423）。
    * 一致が**2件以上** → ``(None, "ambiguous")``。どれが今回の成果物か決められないので
      **解放しない**（呼び出し側が ``stale`` へ落として主文脈の判断へ回す）。
    * ``tmp/_handoff`` が symlink、または存在するがディレクトリではない（regular file 等）
      → ``(None, "unreadable")``。**これは「無い」ではなく「列挙できない」**——symlink は
      構成要素を辿らないと本当に空か分からず、regular file は中身を列挙できない（F-354-07）。
      保留（``empty``）と違い「観測できていない」異常なので ``stale`` へ落とす。
    * 台帳の ``issue`` が整数として読めない → ``(None, "unidentifiable")``。自分の handoff を
      名指しできない＝同じく異常なので ``stale`` へ落とす。
    """
    if not isinstance(issue, int) or isinstance(issue, bool) or issue < 1:
        return None, "unidentifiable"
    directory = Path(repo_root) / worktree_path / HANDOFF_DIR_REL
    if directory.is_symlink():
        return None, "unreadable"
    if not directory.exists():
        return None, "empty"
    if not directory.is_dir():
        return None, "unreadable"
    try:
        children = sorted(
            child for child in directory.iterdir() if not child.is_dir()
        )
    except OSError:
        return None, "unreadable"
    pattern = own_handoff_pattern(agent_type, issue)
    mine = [child for child in children if pattern.fullmatch(child.name)]
    if not mine:
        return None, "empty"
    if len(mine) > 1:
        return None, "ambiguous"
    return f"{HANDOFF_DIR_REL}/{mine[0].name}", "unique"


def _already_deferred(entry: Mapping[str, Any]) -> bool:
    """このエントリに保留の記録が既にあるか（``notes`` の marker で見る）。"""
    notes = entry.get("notes")
    if not isinstance(notes, list):
        return False
    return any(
        isinstance(item, Mapping) and HANDOFF_PENDING_MARKER in str(item.get("note", ""))
        for item in notes
    )


def _defer(
    stderr: TextIO,
    *,
    repo_root: Path,
    entry: Mapping[str, Any],
    entry_id: str,
    now: datetime,
    status: Any,
    agent_type: str,
) -> None:
    """自分の handoff がまだ無い停止を**保留**する（台帳の状態は進めない・Issue #423）。

    状態を進めないので ``mark`` は呼ばない。記録として ``notes`` を1行だけ残す——
    入れ子委譲のたびに停止イベントが届くため毎回積むと台帳が観測ログで埋まり、
    ``update_ledger`` のロック取得回数も無駄に増える（並列 dispatch 下の競合リスク）。
    2回目以降は stderr の evidence だけにする。

    **記録に失敗しても何もしない**（保留は「何もしない」が正しい振る舞いなので、
    記録できないことを理由に状態を動かす必要がない＝fail-safe）。
    """
    if not _already_deferred(entry):
        try:
            worktree_ledger.add_note(
                repo_root,
                entry_id,
                now=now,
                note=(
                    f"SubagentStop: 自分の handoff が未検出のため回収を保留した"
                    f"（{HANDOFF_PENDING_MARKER}）。入れ子委譲待ちの一時停止と区別できないため"
                    "台帳は running のまま進めない（Issue #423）"
                ),
            )
        except Exception as exc:
            _evidence(
                stderr, "stop", result="release-error", reason="ADD_NOTE_FAILED",
                error=type(exc).__name__, entry_id=entry_id,
            )
    _evidence(
        stderr, "stop", result="release-deferred", reason="HANDOFF_PENDING",
        entry_id=entry_id, status=status, agent_type=agent_type,
    )


def _release_stage(
    *,
    stderr: TextIO,
    payload: Mapping[str, Any] | None,
    agent_type: str,
    cwd: Path | None,
    now: datetime,
    runner: Callable[..., subprocess.CompletedProcess],
) -> None:
    """終了した dispatch の worktree を回収してから解放する（Issue #354・PR-3）。

    **stdout には一切書かない**（停止をブロックするのは前段のカルテ検査だけ）。結果は
    stderr の evidence にのみ残す。どの失敗経路でも例外を外へ出さず、worktree を消さずに
    ``stale`` へ落として制御を主文脈へ返す——次 dispatch を gate が
    ``ISSUE_START_WORKTREE_RESIDUE`` で deny するので、取りこぼしは必ず表に出る。

    段:

    1. 台帳の置き場（main worktree root）を導出する
    2. ``agent_id`` で自分のエントリを引く。引けなければ**推測して他人のエントリを潰さず**、
       同 ``agent_type`` の最新 ``open`` エントリだけを ``stale`` へ落とす
       （``open``＝まだ誰の worktree も掴んでいない＝落としても実体は失われない）
    3. **自分の handoff を1つに決める**（:func:`_discover_handoff`）。**台帳を進める前に
       ここを判定する**（Issue #423）——0件なら :func:`_defer` で ``running`` のまま保留し、
       以降の段へ進まない。先に ``stopped`` へ進めてしまうと、保留と判った時点で既に
       residue になっており、gate が同じ dispatch 自身の次の入れ子委譲を拒否する
    4. **``running`` → ``stopped`` へ遷移させる**（F-354-01）。``collect-worktree`` は
       ``running`` を ``WORKTREE_LIVE`` で拒否し ``stopped`` のみ受理するので、この遷移を
       挟まないと自動解放は一度も成功しない
    5. ``python3 -m gitgate collect-worktree`` を起動する。exit 0 以外・起動不能・timeout は
       いずれも ``stale``（**削除しない**）。exit 0 のときの evidence ``result`` は2種に分かれる
       （Issue #464・F-464-05）——``release-ok``＝回収は成功し実体の削除も完了した、
       ``release-deferred``＝回収は成功したが実体の削除は worktree ロックで ``release_pending``
       へ遅延した（成果物は失われていない。削除は次 dispatch の gate が引き取る）。判別は
       ``gitgate collect-worktree`` が stderr へ書く ``released={yes|no}`` を読んで行う。
    """
    agent_id = agent_id_of(payload)
    try:
        repo_root = worktree_ledger.main_worktree_root(_cwd_of(payload, cwd))
    except Exception as exc:
        # 置き場が決まらない＝台帳も引けない。何も消さず、何も書かずに返す。
        _evidence(
            stderr, "stop", result="release-skip", reason="REPO_ROOT_UNRESOLVED",
            error=type(exc).__name__, agent_type=agent_type,
        )
        return

    def stale(entry_id: str, note: str, **fields: Any) -> None:
        try:
            worktree_ledger.mark(repo_root, entry_id, "stale", now=now, note=note)
        except Exception as exc:
            _evidence(
                stderr, "stop", result="release-error", reason="MARK_STALE_FAILED",
                error=type(exc).__name__, entry_id=entry_id, **fields,
            )
            return
        _evidence(stderr, "stop", result="release-stale", entry_id=entry_id, **fields)

    try:
        entry = (
            worktree_ledger.find_by_agent_id(repo_root, agent_id) if agent_id else None
        )
    except Exception as exc:
        _evidence(
            stderr, "stop", result="release-skip", reason="LEDGER_UNREADABLE",
            error=type(exc).__name__, agent_type=agent_type,
        )
        return

    if entry is None:
        # 束縛できなかった（`SubagentStart` の worktree 特定が不能だった／台帳が壊れていた）。
        # **`running` を掴みにいかない**——それは別 dispatch のものかもしれず、`stale` へ
        # 落とすと `WORKTREE_LIVE` の保護が外れて live な worktree を強制解放できてしまう。
        # 落としてよいのは「まだ何も掴んでいない」`open` だけ。
        try:
            orphan = worktree_ledger.latest_open_entry(repo_root, agent_type)
        except Exception as exc:
            _evidence(
                stderr, "stop", result="release-skip", reason="LEDGER_UNREADABLE",
                error=type(exc).__name__, agent_type=agent_type,
            )
            return
        if orphan is None:
            _evidence(
                stderr, "stop", result="release-skip", reason="ENTRY_NOT_FOUND",
                agent_type=agent_type, agent_id=agent_id,
            )
            return
        stale(
            orphan["entry_id"],
            "SubagentStop: 束縛されないまま停止した（回収対象を特定できない）",
            reason="ENTRY_UNBOUND", agent_type=agent_type, agent_id=agent_id,
        )
        return

    entry_id = entry["entry_id"]
    status = entry.get("status")
    if status in ("released", "abandoned"):
        _evidence(
            stderr, "stop", result="release-skip", reason="ALREADY_TERMINAL",
            entry_id=entry_id, status=status,
        )
        return
    if status == worktree_ledger.DEFERRED_RELEASE_STATUS:
        # 回収は完了済みで worktree の物理削除だけが残っている（git ロック待ち・Issue #464）。
        # ロックはこの停止イベントの時点ではまだエージェントプロセスが握っているため、
        # ここで `collect-worktree` を再起動しても無駄。削除は次 dispatch の gate
        # （`assert_no_worktree_residue`）がロックの外れた後に引き取る。
        _evidence(
            stderr, "stop", result="release-skip", reason="RELEASE_PENDING_DEFERRED",
            entry_id=entry_id, status=status,
        )
        return
    if status == "open":
        # 束縛前に停止した（`open` → `stopped` の辺は無い）。実体は掴んでいないので落として安全。
        stale(
            entry_id,
            "SubagentStop: 束縛されないまま停止した（open のまま）",
            reason="ENTRY_UNBOUND", status=status,
        )
        return

    worktree_path = entry.get("worktree_path")
    if not worktree_path:
        stale(
            entry_id,
            "SubagentStop: worktree_path が未束縛のため回収対象を特定できない",
            reason="WORKTREE_UNKNOWN", status=status,
        )
        return

    # --- 「終了」か「一時停止」かの判定（Issue #423） ---------------------------------
    # **台帳を進める前に判定する。** 先に `running` → `stopped` へ進めてしまうと、保留と
    # 判った時点で既に `stopped`（＝residue）になっており、gate が同じ dispatch 自身の
    # 次の入れ子委譲を `ISSUE_START_WORKTREE_RESIDUE` で拒否する（#423 の実害）。
    if status == "collected":
        # 回収は済んでいて解放だけが残っている。**handoff は探さない**——worktree に残った
        # 回収済みファイルや委譲先の handoff を再検出して `ambiguous` で詰まるのを防ぐ
        # （#423 の失敗連鎖 3・5）。`gitgate` 側も `collected` なら回収段を飛ばす。
        handoff, how = None, "already-collected"
    else:
        handoff, how = _discover_handoff(
            repo_root, worktree_path, agent_type=agent_type, issue=entry.get("issue")
        )
        if how == "empty":
            # 自分の handoff がまだ無い＝終了したのか入れ子委譲待ちの一時停止なのか決められない。
            # **台帳を一切進めない**（`running` のまま）。停止はブロックしないので、当の
            # dispatch はそのまま次の委譲へ進める。本当に終了していれば handoff を書いた
            # あとの停止イベントで回収される。
            _defer(
                stderr, repo_root=repo_root, entry=entry, entry_id=entry_id,
                now=now, status=status, agent_type=agent_type,
            )
            return
        if handoff is None:
            stale(
                entry_id,
                f"SubagentStop: 回収対象の handoff を一意に決められない（{how}）",
                reason="HANDOFF_AMBIGUOUS", how=how, status=status,
            )
            return

    if status == "running":
        try:
            worktree_ledger.mark(
                repo_root, entry_id, "stopped", now=now,
                note="SubagentStop: 所有者 dispatch の停止を確認した（自分の handoff を検出）",
            )
        except Exception as exc:
            _evidence(
                stderr, "stop", result="release-error", reason="MARK_STOPPED_FAILED",
                error=type(exc).__name__, entry_id=entry_id,
            )
            return
        status = "stopped"

    argv = collect_worktree_argv(entry_id, handoff=handoff)
    try:
        completed = runner(
            argv, cwd=str(repo_root), text=True, capture_output=True,
            shell=False, timeout=COLLECT_TIMEOUT_S,
        )
    except Exception as exc:
        stale(
            entry_id,
            f"SubagentStop: collect-worktree を完了できなかった（{type(exc).__name__}）",
            reason="COLLECT_UNRUNNABLE", error=type(exc).__name__,
        )
        return
    returncode = getattr(completed, "returncode", None)
    if returncode != 0:
        detail = (getattr(completed, "stderr", "") or "").strip()[:400]
        stale(
            entry_id,
            f"SubagentStop: collect-worktree が exit {returncode}"
            + (f"（{detail}）" if detail else ""),
            reason="COLLECT_FAILED", exit_code=returncode,
        )
        return
    # `gitgate collect-worktree` は exit 0 でも実際に解放できたとは限らない
    # （Issue #464：worktree ロックで削除だけ遅延し ``release_pending`` に留まる場合がある）。
    # `gitgate/cli.py::_run_worktree_verb` が stderr へ書く
    # ``released={yes|no}`` を読み、``released=no`` のときは ``release-deferred`` として
    # evidence を分ける（F-464-05）。**``release-ok`` は「回収は成功した・解放済みとは限らない」
    # ことを意味する**——判別できない旧形式の出力（stderr が空/読めない等）は安全側で
    # ``release-ok`` のまま扱う（誤って deferred だと騒ぐより、後段の gate deny が実際の
    # 残留を必ず拾うので実害は無い）。
    release_detail = (getattr(completed, "stderr", "") or "")
    result = "release-deferred" if "released=no" in release_detail else "release-ok"
    _evidence(
        stderr, "stop", result=result, entry_id=entry_id,
        worktree_path=worktree_path, handoff=handoff, how=how,
    )


def run_stop(
    *,
    stdin: TextIO,
    stdout: TextIO,
    stderr: TextIO,
    cwd: Path | None = None,
    now: datetime | None = None,
    runner: Callable[..., subprocess.CompletedProcess] = subprocess.run,
) -> int:
    """``SubagentStop``：カルテ未更新のまま ``issue-fixer`` を停止させない。

    段（**前段で block したら後段へ進まない**）:

    1. ``agent_type`` が対象外 → stdout 無出力・stderr に evidence・exit 0
    2. ``agent_type == "issue-fixer"``: :func:`_karte_stop_gate`。``active.json`` の
       ``{issue, round}`` で ``python3 -m karte check`` を実行し、非0 または判定不能なら
       ``{"decision":"block","reason": …}`` を stdout に出して exit 0
       （**再入＝``stop_hook_active`` のときは判定せず通す**＝F-309-02）
    3. :func:`_release_stage`（Issue #354・PR-3）。**自分の handoff を検出できたときだけ**
       ``running`` → ``stopped`` へ進めて ``gitgate collect-worktree`` で回収→解放する。
       検出できなければ ``running`` のまま保留する（Issue #423：入れ子委譲待ちの一時停止と
       区別できないため）。**失敗しても停止をブロックしない**
       （``stale`` へ落として次 dispatch の gate deny へ委ねる）
    4. 無出力 exit 0

    **``repo_root`` の導出は 2 の内側**（F-309-06）。``issue-implementer`` はこの段を
    通らないので、台帳パスの導出失敗（``.git`` 破損等）で無関係な dispatch を
    未捕捉例外＝exit 1 に巻き込まない。3 も同様に自分で導出し、失敗しても例外を外へ出さない。

    **3 を同じスクリプトの逐次段にするのは意図的**（別フックに分けない）。同一イベントに
    「ブロックするフック」と「削除するフック」を別々に登録すると、ブロックされて継続した
    エージェントの worktree を別フックが消す致命的な競合が起きる。単一決定点にすることで
    「block したら解放段へ進まない」が構造的に保証される（``blocked is not None`` で
    return する形が、その保証を型で表している）。
    """
    payload = load_payload(stdin)
    agent_type = agent_type_of(payload)
    if agent_type not in TARGET_ROLES:
        return _skip_evidence(stderr, "stop", payload, agent_type)

    if agent_type == KARTE_ROLE:
        blocked = _karte_stop_gate(
            stdout=stdout, stderr=stderr, payload=payload, cwd=cwd, runner=runner
        )
        if blocked is not None:
            # block した＝エージェントは継続する。**その worktree を消してはならない。**
            return blocked

    # --- 3. 回収・解放段 -----------------------------------------------------------
    _release_stage(
        stderr=stderr, payload=payload, agent_type=agent_type, cwd=cwd,
        now=datetime.now(timezone.utc) if now is None else now, runner=runner,
    )
    return 0


# --- entry point ---------------------------------------------------------------


_VERBS = {
    "karte-inject": lambda: run_karte_inject(
        stdin=sys.stdin, stdout=sys.stdout, stderr=sys.stderr
    ),
    "bind": lambda: run_bind(stdin=sys.stdin, stdout=sys.stdout, stderr=sys.stderr),
    "stop": lambda: run_stop(stdin=sys.stdin, stdout=sys.stdout, stderr=sys.stderr),
}


def main(argv: Sequence[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 1 or args[0] not in _VERBS:
        sys.stderr.write(
            "usage: python3 -m issue_start.subagent_hooks {" + "|".join(_VERBS) + "}\n"
        )
        # フックとしては「何も出力せず素通し」が安全側。usage ミスで dispatch を
        # 巻き込まないよう exit 0 を返す（統制はこの verb では行っていない）。
        return 0
    return _VERBS[args[0]]()


if __name__ == "__main__":
    raise SystemExit(main())
