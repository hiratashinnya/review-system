"""``SessionStart`` フック実体：``release_pending`` の worktree をフル掃除する（Issue #464・F-464-06）。

毎 dispatch の ``issue-start-gate``（:func:`issue_start.gate._finish_deferred_releases`）は
``cleanup_branch_ref=False`` で ``git worktree remove`` の再試行だけを行い、``git fetch`` を
伴うローカルブランチ ref 掃除（:func:`gitgate.worktree._cleanup_branch_ref`）をホットパスから
外している。理由は2経路のトレードオフ：

* **毎 dispatch（このモジュールではない方）**：``git worktree remove`` はローカル操作で
  ロック時は即失敗するため安価。mid-session の ``release_pending`` 溜まりを抑制できるが、
  停止直後のエージェントプロセスがまだ生きていることが多く削除は失敗しがち。
* **``SessionStart``（このモジュール）**：セッション開始時に1回だけ発火する。前セッションの
  ロック保持者 pid は既に死んでいるため、stale ロックが外れて削除が実際に成功しやすい。
  ここで ``cleanup_branch_ref=True``（:func:`gitgate.worktree.worktree_release` の既定）の
  フル掃除を行い、branch ref 掃除・``git fetch`` もこの「1セッション1回」の頻度に抑える。

**fail-close は弱めない**：ここでの削除・branch ref 掃除はいずれもベストエフォートで、
deny 網の代替ではない。失敗しても ``release_pending`` のまま持ち越され、
``issue-start-gate``（:func:`issue_start.gate.assert_no_worktree_residue`）の
residue/stale 判定と次 dispatch の deny は従来どおり効く
（連続失敗回数の escalation は F-464-02 が毎 dispatch 側に実装済み。ここは重複させない
——SessionStart は「消せるものを消す」だけの副次的な掃除役に留める）。

出力契約は他の SessionStart hook（``install_pkgs.sh``）と同様の非対話・fail-open：
判定できない／実行できない場合は黙って exit 0。診断は stderr の evidence 1行に残す
（``.claude/hooks/README.md`` と同じ様式）。

依存仕様:
  * :func:`issue_start.worktree_ledger.deferred_release_entries`（対象エントリの読取）
  * :func:`gitgate.worktree.worktree_release`（``cleanup_branch_ref`` 引数・Issue #464 F-464-06）
  ※ いずれも out-of-graph（版なし）。本モジュールは
    `.claude/rules/02-decision-process.md`「起票先はプロジェクト区分で決める」の
    **汎用開発ハーネス**区分（Issue 運用パイプライン）に属する。
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, TextIO

from . import worktree_ledger


def _evidence(stderr: TextIO, **fields: Any) -> None:
    payload = {"hook": "session-start-worktree-release", **fields}
    stderr.write(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
    )


def run(
    *,
    stdout: TextIO,
    stderr: TextIO,
    cwd: Path | None = None,
    now: datetime | None = None,
    runner: Callable[..., subprocess.CompletedProcess] = subprocess.run,
) -> int:
    """``release_pending`` エントリのフル解放（削除＋branch ref 掃除）を試みる（best-effort）。

    **stdout は常に無出力 exit 0**（``SessionStart`` は統制を行わない副次的な掃除役——
    判定・deny はすべて ``issue-start-gate`` 側に残る）。結果は stderr の evidence にのみ残す。
    """
    from gitgate.worktree import WorktreeError, worktree_release

    stamp = datetime.now(timezone.utc) if now is None else now
    try:
        root = worktree_ledger.main_worktree_root(Path.cwd() if cwd is None else Path(cwd))
    except Exception as exc:  # noqa: BLE001 - best-effort: 置き場が決まらなければ何もしない
        _evidence(stderr, result="skip", reason="REPO_ROOT_UNRESOLVED", error=type(exc).__name__)
        return 0
    try:
        entries = worktree_ledger.deferred_release_entries(root)
    except Exception as exc:  # noqa: BLE001 - best-effort: 台帳が読めなければ何もしない
        _evidence(stderr, result="skip", reason="LEDGER_UNREADABLE", error=type(exc).__name__)
        return 0

    finished: list[dict[str, Any]] = []
    for entry in entries:
        entry_id = entry.get("entry_id")
        worktree_path = entry.get("worktree_path")
        if (
            not isinstance(entry_id, str)
            or not isinstance(worktree_path, str)
            or not worktree_path
        ):
            continue
        try:
            # `cleanup_branch_ref` は既定 True（フル掃除・Issue #464 F-464-06）。
            outcome = worktree_release(
                root,
                worktree_path,
                entry_id=entry_id,
                reason=(
                    "session-start: 遅延していた解放をセッション開始時にフル掃除した"
                    "（Issue #464）"
                ),
                now=stamp,
                runner=runner,
            )
        except Exception as exc:  # noqa: BLE001 - best-effort: 失敗しても release_pending のまま
            reason = exc.reason if isinstance(exc, WorktreeError) else type(exc).__name__
            finished.append({"entry_id": entry_id, "released": False, "error": reason})
            continue
        finished.append({"entry_id": entry_id, "released": outcome.status == "released"})
    _evidence(stderr, result="done", finished=finished)
    return 0


def main(argv: Any = None) -> int:
    return run(stdout=sys.stdout, stderr=sys.stderr)


if __name__ == "__main__":
    raise SystemExit(main())
