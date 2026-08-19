"""``SubagentStart`` / ``SubagentStop`` フックの実体（Issue #309・PR-1）。

3つの verb を1モジュールに束ねる（``.claude/hooks/*.sh`` はそれぞれ薄い起動口）:

===================  =====================  ==========================================
verb                 イベント / matcher     役割
===================  =====================  ==========================================
``karte-inject``     SubagentStart          ``issue-fixer`` へカルテ手順を
                     ``issue-fixer``        ``additionalContext`` として注入する（助言）
``bind``             SubagentStart          起動した dispatch の worktree を所有台帳へ
                     implementer / fixer    束縛する（``open`` → ``running``）
``stop``             SubagentStop           カルテ未更新のまま停止させない（block）
                     implementer / fixer    ＋ **PR-3 の回収・解放段の seam**
===================  =====================  ==========================================

**本 PR（PR-1）は何も削除せず、dispatch も1つも deny しない。**
``stop`` は ``issue-fixer`` のカルテ検査で「停止」を拒否することはあるが、worktree の
削除経路は**1つも実装していない**（``git worktree remove`` を呼ぶコードが存在しない）。

fail 方針の非対称（設計判断・``.claude/hooks/README.md`` にも明記）
------------------------------------------------------------------
* **停止のブロックは fail-close**：``issue-fixer`` のカルテ判定が**不能**なら block する
  （``active.json`` 欠如・破損・``karte check`` を起動できない、を含む）。
* **worktree の削除は fail-safe＝「消さない」側に倒す**（PR-3 で実装する解放段の方針）。
* 両者は**方向が逆**である。ブロックの誤りは「余計に止まる」だけで回復可能だが、削除の
  誤りは成果物を回復不能に失う。削除しなかったぶんの残留は PR-3 の gate deny が拾う。

対象外ロールの扱い
------------------
``agent_type`` が対象外・欠落・payload が読めない場合は **常に無出力 exit 0**
（``agent-command-gate.sh`` の「対象外ロールは常に許可」不変条件と同型）。**この
in-script 判定があるので、要実測事項 V-2（``matcher`` が ``agent_type`` 名で効くか）の
結果がどちらでも契約は成立する**——matcher が効けば発火自体が絞られ、効かなければ
ここで無出力 exit 0 になる。

依存仕様:
  * :mod:`issue_start.worktree_ledger`（台帳 API・状態遷移）
  * ``karte`` CLI の ``check``（終了コード 0=OK / 2=未検出 / 4=前提違反）
  * ``karte/cli.py`` の進行ポインタ規約（``tmp/_karte/active.json`` の ``{issue, round}``）
"""

from __future__ import annotations

import json
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


def _block(stdout: TextIO, reason: str) -> int:
    """``SubagentStop`` の停止拒否。**exit code は 0 のまま**（既存ハーネスの前提を壊さない）。"""
    json.dump({"decision": "block", "reason": reason}, stdout, ensure_ascii=False)
    stdout.write("\n")
    return 0


# --- verb: karte-inject（SubagentStart・matcher issue-fixer） --------------------


def run_karte_inject(
    *,
    stdin: TextIO,
    stdout: TextIO,
    stderr: TextIO,
    project_root: Path | None = None,
) -> int:
    """カルテ手順を ``additionalContext`` として注入する（注入は助言＝fail-open）。

    **フックはデータを押し込まない**——``SubagentStart`` payload に dispatch prompt が
    無いため、``{issue, round}`` の解決は注入本文が指示する ``karte`` CLI 側
    （``tmp/_karte/active.json`` からの補完）に委ねる。注入本文をシェルから分離して
    ``.claude/hooks/karte-protocol.md`` に置くのは ``inject-governance.sh`` と同作法。
    """
    payload = load_payload(stdin)
    agent_type = agent_type_of(payload)
    if agent_type != KARTE_ROLE:
        return 0
    root = PACKAGE_ROOT if project_root is None else Path(project_root)
    protocol = root / KARTE_PROTOCOL_REL
    try:
        body = protocol.read_text(encoding="utf-8").strip()
    except OSError as exc:
        _evidence(stderr, "karte-inject", result="skip", error=f"{type(exc).__name__}")
        return 0
    if not body:
        _evidence(stderr, "karte-inject", result="skip", error="EMPTY_PROTOCOL")
        return 0
    json.dump(
        {
            "hookSpecificOutput": {
                "hookEventName": "SubagentStart",
                "additionalContext": body,
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
        return 0
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


def run_stop(
    *,
    stdin: TextIO,
    stdout: TextIO,
    stderr: TextIO,
    cwd: Path | None = None,
    runner: Callable[..., subprocess.CompletedProcess] = subprocess.run,
) -> int:
    """``SubagentStop``：カルテ未更新のまま ``issue-fixer`` を停止させない。

    段（**前段で block したら後段へ進まない**）:

    1. ``agent_type`` が対象外 → 無出力 exit 0
    2. ``agent_type == "issue-fixer"``: ``active.json`` の ``{issue, round}`` で
       ``python3 -m karte check`` を実行し、非0 または判定不能なら
       ``{"decision":"block","reason": …}`` を stdout に出して exit 0
    3. （**PR-3 で追加する回収・解放段の seam**）
    4. 無出力 exit 0

    **3 を同じスクリプトの逐次段にするのは意図的**（別フックに分けない）。同一イベントに
    「ブロックするフック」と「削除するフック」を別々に登録すると、ブロックされて継続した
    エージェントの worktree を別フックが消す致命的な競合が起きる。単一決定点にすることで
    「block したら解放段へ進まない」が構造的に保証される。
    """
    payload = load_payload(stdin)
    agent_type = agent_type_of(payload)
    if agent_type not in TARGET_ROLES:
        return 0

    repo_root = worktree_ledger.main_worktree_root(_cwd_of(payload, cwd))

    if agent_type == KARTE_ROLE:
        try:
            issue, round_no = read_active_pointer(repo_root)
        except ActivePointerError as exc:
            _evidence(stderr, "stop", result="block", reason="ACTIVE_POINTER_UNREADABLE")
            return _block(
                stdout,
                "issue-fixer の停止を拒否する（Issue #309・判定不能は fail-close）: "
                f"{exc}\n"
                "主文脈が `python3 -m karte ingest-review --issue <N> --round <R> --from -` を"
                "実行して進行ポインタを作り直すこと（ingest-review は是正当事者には許さない）。",
            )
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

    # --- 3. 回収・解放段（PR-3 で実装する seam） ---------------------------------
    # 本 PR は worktree を1つも削除しない。ここに `collect-worktree`（回収→検証→解放）を
    # 足すのは PR-3（`gitgate` の verb 実装＝PR-2 に依存）。**削除経路を先に作らない**のは
    # 「統制を先に、付与は別 PR」の順序を守るため（観測が正確になったことを実測してから
    # 解放を有効化する）。
    _evidence(stderr, "stop", result="allow", agent_type=agent_type, release_stage="deferred-to-PR-3")
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
