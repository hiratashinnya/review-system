"""依頼文ファイルと最終応答ファイルの受け渡し（Issue #538 D8）。

gated ロールのシェルでは `<` `>` `|` が使えないため、依頼文はファイルで受け取り、
Codex の最終応答は `--output-last-message` でファイルへ書かせる。
"""

from __future__ import annotations

from pathlib import Path

from .errors import CodexExecError

MAX_PROMPT_BYTES = 262_144


def read_prompt(path: Path, cwd: Path) -> str:
    """symlink でない通常ファイルを UTF-8 で読む。空・過大・読めないものは拒否する。"""
    target = cwd / path
    if target.is_symlink() or not target.is_file():
        raise CodexExecError("CODEX_EXEC_PROMPT_UNREADABLE", str(target))
    try:
        data = target.read_bytes()
        text = data.decode("utf-8")
    except (OSError, UnicodeDecodeError) as error:
        raise CodexExecError("CODEX_EXEC_PROMPT_UNREADABLE", f"{target}: {error}") from None
    if not text.strip() or len(data) > MAX_PROMPT_BYTES:
        raise CodexExecError("CODEX_EXEC_PROMPT_UNREADABLE", f"{target}: {len(data)} bytes")
    return text


def resolve_output_target(path: Path, cwd: Path) -> Path:
    """書き先の親ディレクトリが実在し、書き先が symlink・ディレクトリでないことを確かめる。"""
    target = cwd / path
    if target.is_symlink() or target.is_dir() or not target.parent.is_dir():
        raise CodexExecError("CODEX_EXEC_OUTPUT_INVALID", str(target))
    return target.parent.resolve() / target.name
