"""依頼文ファイルと最終応答ファイルの受け渡し（Issue #538 D8）。

gated ロールのシェルでは `<` `>` `|` が使えないため、依頼文はファイルで受け取り、
Codex の最終応答は `--output-last-message` でファイルへ書かせる。
"""

from __future__ import annotations

from pathlib import Path

from .errors import CodexExecError

MAX_PROMPT_BYTES = 262_144


def _resolve_tmp_target(path: Path, cwd: Path, worktree: Path, error_id: str) -> Path:
    target = cwd / path
    try:
        tmp = worktree.resolve() / "tmp"
        resolved = target.resolve()
        valid = (
            not target.is_symlink() and tmp.is_dir() and tmp.resolve(strict=True) == tmp
            and resolved != tmp and resolved.is_relative_to(tmp)
        )
    except (OSError, RuntimeError):
        valid = False
    if not valid:
        raise CodexExecError(error_id, f"worktree tmp boundary: {target}")
    return resolved


def read_prompt(path: Path, cwd: Path, worktree: Path) -> str:
    """symlink でない通常ファイルを UTF-8 で読む。空・過大・読めないものは拒否する。"""
    target = _resolve_tmp_target(path, cwd, worktree, "CODEX_EXEC_PROMPT_UNREADABLE")
    if not target.is_file():
        raise CodexExecError("CODEX_EXEC_PROMPT_UNREADABLE", str(target))
    try:
        data = target.read_bytes()
        text = data.decode("utf-8")
    except (OSError, UnicodeDecodeError) as error:
        raise CodexExecError("CODEX_EXEC_PROMPT_UNREADABLE", f"{target}: {error}") from None
    if not text.strip() or len(data) > MAX_PROMPT_BYTES:
        raise CodexExecError("CODEX_EXEC_PROMPT_UNREADABLE", f"{target}: {len(data)} bytes")
    return text


def resolve_output_target(path: Path, cwd: Path, worktree: Path) -> Path:
    """書き先の親ディレクトリが実在し、書き先が symlink・ディレクトリでないことを確かめる。"""
    target = _resolve_tmp_target(path, cwd, worktree, "CODEX_EXEC_OUTPUT_INVALID")
    if target.is_dir() or not target.parent.is_dir():
        raise CodexExecError("CODEX_EXEC_OUTPUT_INVALID", str(target))
    return target
