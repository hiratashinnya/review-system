"""``PostToolUse``（matcher ``Bash``）フックの実体（Issue #512）。

``karte ingest-review`` / ``karte close-attempt`` の実行を検出し、``karte status --json`` を
起動して :mod:`karte_notify.notify` の判定に通したうえで、通知が必要なら ``systemMessage``
フィールドでオーナーのチャットへ直送する。**``systemMessage`` はモデルの出力を経由せず
ユーザーのターミナルへ表示される**（Claude Code の hook 出力契約）ため、AI の要約を経ずに
機械判定を届けるという Issue #512 の目的そのものを満たす（対照的に ``hookSpecificOutput.
additionalContext`` は AI のコンテキストへ入るだけで、その後の要約過程で歪みうる——
実際に PR #509／Issue #431 で起きた）。

対象外・判定不能な経路はすべて**無出力 exit 0**（``issue_start.subagent_hooks`` と同じ
「対象外ロールは常に許可」不変条件と同型）。本フックは統制（deny）を行わない可視化専用の
助言機構であり、``PostToolUse`` はそもそもツール呼び出しをブロックできない
（``karte/cli.py::cmd_status`` の docstring と同じ理由）。診断は stderr の evidence（1行1 JSON）
へ残す（``claude --debug`` で拾える）。

依存仕様:
  * GitHub Issue #512
  * :mod:`karte_notify.notify`（通知要否の判定・既読スナップショット I/O）
  * ``karte/cli.py::_status_payload``（``karte status --json`` の出力スキーマ）
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable, Mapping, TextIO

from karte import paths as karte_paths

from . import notify

# ``karte_notify/`` の親＝リポジトリルート（起動口シェルスクリプトが `$CLAUDE_PROJECT_DIR` へ
# cd してから `python3 -m karte_notify.hook` を呼ぶ前提。`issue_start/subagent_hooks.py` の
# `PACKAGE_ROOT` と同じ導出）。
PACKAGE_ROOT = Path(__file__).resolve().parent.parent
STATUS_TIMEOUT_S = 30.0


def _load_payload(stdin: TextIO) -> dict | None:
    try:
        value = json.load(stdin)
    except (json.JSONDecodeError, UnicodeDecodeError, ValueError, OSError):
        return None
    return value if isinstance(value, dict) else None


def _evidence(stderr: TextIO, **fields: Any) -> None:
    stderr.write(
        json.dumps({"hook": "karte-notify", **fields}, ensure_ascii=False, sort_keys=True)
        + "\n"
    )


def _status_payload(
    repo_root: Path,
    issue: int | None,
    runner: Callable[..., subprocess.CompletedProcess],
) -> dict | None:
    """``karte status --json`` を起動して payload を返す（失敗すれば ``None``＝fail-open）。

    ``issue`` を明示できないとき（``--issue`` が Bash コマンドから取れないとき）は省略する。
    ``karte status`` 自身が進行ポインタ（``tmp/_karte/active.json``）から補完する
    （``karte/cli.py::_resolve_issue`` と同じ規約）。
    """
    argv = [sys.executable, "-m", "karte", "status", "--json"]
    if issue is not None:
        argv += ["--issue", str(issue)]
    try:
        completed = runner(
            argv, cwd=str(repo_root), text=True, capture_output=True,
            shell=False, timeout=STATUS_TIMEOUT_S,
        )
    except Exception:
        return None
    if getattr(completed, "returncode", None) != 0:
        return None
    try:
        payload = json.loads(getattr(completed, "stdout", "") or "")
    except ValueError:
        return None
    return payload if isinstance(payload, dict) else None


def run(
    *,
    stdin: TextIO,
    stdout: TextIO,
    stderr: TextIO,
    project_root: Path | None = None,
    runner: Callable[..., subprocess.CompletedProcess] = subprocess.run,
) -> int:
    payload = _load_payload(stdin)
    if payload is None:
        return 0
    if payload.get("tool_name") != "Bash":
        return 0
    tool_input = payload.get("tool_input")
    command = tool_input.get("command") if isinstance(tool_input, Mapping) else None
    if not isinstance(command, str):
        return 0
    verb = notify.detect_trigger(command)
    if verb is None:
        return 0

    root = PACKAGE_ROOT if project_root is None else Path(project_root)
    try:
        repo_root = karte_paths.main_worktree_root(root)
    except Exception as exc:
        _evidence(stderr, result="skip", reason="REPO_ROOT_UNRESOLVED", error=type(exc).__name__)
        return 0

    issue = notify.issue_from_command(command)
    status_payload = _status_payload(repo_root, issue, runner)
    if status_payload is None:
        _evidence(stderr, result="skip", reason="STATUS_UNAVAILABLE", verb=verb, issue=issue)
        return 0

    resolved_issue = status_payload.get("issue")
    if not isinstance(resolved_issue, int):
        _evidence(stderr, result="skip", reason="ISSUE_UNRESOLVED", verb=verb)
        return 0

    try:
        snapshot_path = notify.notified_snapshot_path(repo_root, resolved_issue, create_dir=True)
    except Exception as exc:
        _evidence(
            stderr, result="skip", reason="SNAPSHOT_PATH_ERROR",
            error=type(exc).__name__, issue=resolved_issue,
        )
        return 0

    previous = notify.read_snapshot(snapshot_path)
    message, snapshot = notify.decide(status_payload, previous)

    try:
        notify.write_snapshot(snapshot_path, snapshot)
    except Exception as exc:
        # 書けなくても通知自体は届ける（fail-open：既読管理の欠落は次回の重複表示に留まり、
        # 「判定がオーナーへ届かない」という本 Issue が塞ぐ穴よりはるかに実害が小さい）。
        _evidence(
            stderr, result="write-error", error=type(exc).__name__, issue=resolved_issue,
        )

    if message is None:
        _evidence(stderr, result="silent", issue=resolved_issue, verb=verb)
        return 0

    json.dump({"systemMessage": message}, stdout, ensure_ascii=False)
    stdout.write("\n")
    _evidence(stderr, result="notified", issue=resolved_issue, verb=verb, chars=len(message))
    return 0


def main() -> int:
    return run(stdin=sys.stdin, stdout=sys.stdout, stderr=sys.stderr)


if __name__ == "__main__":
    raise SystemExit(main())
