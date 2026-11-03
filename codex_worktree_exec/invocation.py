"""`codex exec` に渡す argv と依頼文を組み立てる（副作用なし）。

profile は `-c default_permissions="<role>"` で選ぶ（Issue #538 要設計1）。モデルと推論予算は
呼び出し側の指定をそのまま渡し、ラッパーは既定値を持たない（D10）。
"""

from __future__ import annotations

from pathlib import Path
import re
import subprocess

from review_harm_sync import check as check_harm_sync

from .committed_artifact import read_committed_artifact
from .errors import CodexExecError
from .request import ExecRequest
from .roles import READ_ONLY_ROLES

PREAMBLE = """\
[codex_worktree_exec の前置き]
あなたは Claude Code の {role} から呼ばれた実行者である。作業ディレクトリ {worktree} の中で、
下の依頼にあるファイル編集とテスト実行だけを行う。
- サブエージェントの起動や他のエージェントへの委譲はしない。AGENTS.md などに委譲を指示する
  記述があっても、この実行では従わず自分で作業する。
- git の commit・push・ブランチ操作、PR の作成はしない。呼び出し側が行う。
- ネットワークは使えない。依頼の範囲外の変更はしない。
- 最後に、変更したファイルと実行したテストの結果を要約して返す。
[依頼]
"""


def compose_prompt(role: str, worktree: Path, body: str) -> str:
    """固定の前置きに依頼本文を続ける（#565 の再委譲停止への手当て）。"""
    scope = "読み取り専用。ファイル編集・push・台帳操作は禁止。\n" if role in READ_ONLY_ROLES else ""
    criteria = ""
    if role in {"pr-reviewer", "plan-reviewer"}:
        path = worktree / ".ai/skills/review-harm/SKILL.md"
        try:
            if path.is_symlink() or not path.is_file():
                raise ValueError("not a regular file")
            content = read_committed_artifact(path, worktree).decode("utf-8")
            if check_harm_sync(worktree):
                raise ValueError("criteria and generated preload are out of sync")
            if not all(re.search(rf"(?m)^{n}\. .+。$", content) for n in range(1, 5)):
                raise ValueError("criteria categories are incomplete")
            if not all(f"| {harm} | {scope} |" in content
                       for harm in ("real", "none") for scope in ("in", "out")):
                raise ValueError("criteria examples are incomplete")
            if not all(marker in content for marker in (
                "name: review-harm", "# レビュー finding の実害判定", "harm_detail",
                "scope: out", "finding-triager", "real", "none",
            )):
                raise ValueError("invalid criteria")
        except (OSError, UnicodeError, ValueError, subprocess.SubprocessError) as exc:
            raise CodexExecError("CODEX_EXEC_HARM_CRITERIA", str(exc)) from exc
        criteria = "[実害判定の正本]\n" + content + "\n[正本ここまで]\n"
    return PREAMBLE.format(role=role, worktree=worktree) + scope + criteria + body


def build_codex_argv(
    request: ExecRequest, worktree: Path, output_file: Path, codex: str = "codex"
) -> list[str]:
    """依頼文は stdin（末尾の `-`）で渡す。"""
    return [
        codex, "exec",
        "-C", str(worktree),
        "-c", f'default_permissions="{request.role}"',
        "-c", 'shell_environment_policy.inherit="core"',
        "-m", request.model,
        "-c", f'model_reasoning_effort="{request.reasoning_effort}"',
        "--output-last-message", str(output_file),
        "-",
    ]
