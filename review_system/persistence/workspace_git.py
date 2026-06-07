"""DS3 finding-commit ワークスペース（内部 git）。design/05・DD5・S4。

実行ごとに対象を作業コピーへ展開し `git` を subprocess 駆動。finding 単位コミット（Q3）、
実行内失敗は基準点へ reset（all-or-nothing＝S4）、revert で個別/実行ぶんを戻す（O-6）。
git バイナリ前提（DD5）。Python 外部依存なし（stdlib subprocess）。
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

from ..domain.ids import ExecutionId

_SAFE = re.compile(r"[^A-Za-z0-9._-]")
# 一時 git のコミット author＋署名無効（環境の git 設定に依存しない）
_IDENT = [
    "-c", "user.email=reviewer@local", "-c", "user.name=reviewer",
    "-c", "commit.gpgsign=false",
]


def _safe_join(wd: Path, rel: str) -> Path:
    """`rel` を `wd` 配下の安全なパスに解決。絶対パス・`..` 脱出は ValueError（書込前に弾く）。"""
    target = (wd / rel).resolve()
    try:
        target.relative_to(wd.resolve())
    except ValueError:
        raise ValueError(f"ワークスペース外への書込は不可: {rel!r}")
    return target


class GitWorkspaceRepository:
    def __init__(self, root: Path) -> None:
        self.root = root
        self._baseline: dict[str, str] = {}

    def workdir(self, exec_id: ExecutionId) -> Path:
        return self.root / _SAFE.sub("-", exec_id.value)

    def open(self, exec_id: ExecutionId, files: dict[str, str]) -> None:
        """対象を作業コピーへ展開し git init、基準点コミットを打つ。"""
        wd = self.workdir(exec_id)
        wd.mkdir(parents=True, exist_ok=True)
        for rel, content in files.items():
            p = _safe_join(wd, rel)             # 脱出パスは拒否（防御の二重化）
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding="utf-8")
        self._run(wd, "init", "-q")
        self._run(wd, "add", "-A")
        self._run(wd, *_IDENT, "commit", "-q", "-m", "baseline")
        self._baseline[exec_id.value] = self._head(wd)

    def commit_fix(self, exec_id: ExecutionId, finding_id: str, rel_path: str, new_content: str) -> str:
        """1 finding 分の修正を書き込み、finding 単位でコミットして commit ref を返す。"""
        wd = self.workdir(exec_id)
        target = _safe_join(wd, rel_path)        # LLM 由来の脱出パスをここで弾く（[10]）
        target.write_text(new_content, encoding="utf-8")
        self._run(wd, "add", str(target.relative_to(wd.resolve())))
        self._run(wd, *_IDENT, "commit", "-q", "-m", f"{exec_id.value} {finding_id}")
        return self._head(wd)

    def rollback_execution(self, exec_id: ExecutionId) -> None:
        """実行内のいずれかが失敗 → 基準点へ全戻し（書込ゼロ＝S4 all-or-nothing）。"""
        baseline = self._baseline.get(exec_id.value)
        if baseline is None:                     # 基準点が無い（open 失敗等）＝戻すものが無い
            return
        self._run(self.workdir(exec_id), "reset", "--hard", "-q", baseline)

    def revert(self, exec_id: ExecutionId, commit_ref: str) -> None:
        """指定コミットを revert（個別 finding／実行ぶんを戻す＝O-6）。"""
        wd = self.workdir(exec_id)
        self._run(wd, *_IDENT, "revert", "--no-edit", commit_ref)

    def _head(self, wd: Path) -> str:
        return self._run(wd, "rev-parse", "HEAD").stdout.strip()

    def _run(self, wd: Path, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            ["git", *args], cwd=wd, check=True, text=True, capture_output=True,
        )
