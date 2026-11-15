"""Validate handoff source and collection destination paths."""

from __future__ import annotations
import re
from .worktree_models import WorktreeError
from .worktree_arg_common import _reject_control_chars

HANDOFF_DIR_PARTS = ("tmp", "_handoff")
HANDOFF_FILENAME_RE = re.compile(
    r"^(?P<agent>[A-Za-z0-9][A-Za-z0-9._-]*)--issue-(?P<issue>[0-9]+)"
    r"(?P<suffix>-[A-Za-z0-9._-]*)?\.yaml$"
)
_SAFE_PATH_PART_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")

def validate_handoff_relpath(value: str, *, expected_issue: int | None = None) -> str:
    """handoff の「作業ツリールート相対」パスを6条件で検証する。

    `.claude/agents/issue-implementer.md` / `issue-fixer.md` の「``handoff_path`` の検査」と
    同一の規則（symlink 検査＝条件6 だけは FS を見るため :func:`resolve_within` が担当）:

    1. 相対パスであること（先頭 ``/``・``~``・ドライブレターを拒否）
    2. パス要素に ``..`` を含まないこと（正規化で吸収しない）
    3. ``tmp/_handoff/`` 直下のファイル1つであること（要素ちょうど3つ）
    4. ファイル名が ``<agent>--issue-<N>`` で始まり、``issue-<N>`` の直後が ``-`` か ``.``
       であること（``expected_issue`` を渡すと ``<N>`` の一致も見る）
    5. サフィックス部の文字種が ``[A-Za-z0-9._-]`` に限られること
    6. （FS 側）構成要素に symlink が無いこと
    """
    if not isinstance(value, str) or not value:
        raise WorktreeError("COLLECT_HANDOFF_PATH_EMPTY", repr(value))
    _reject_control_chars(value, "handoff path")
    if value.startswith("~") or value.startswith("/"):
        raise WorktreeError("COLLECT_HANDOFF_PATH_NOT_RELATIVE", value)
    if len(value) > 1 and value[1] == ":":
        raise WorktreeError("COLLECT_HANDOFF_PATH_NOT_RELATIVE", value)
    if "\\" in value:
        raise WorktreeError("COLLECT_HANDOFF_PATH_SEPARATOR_INVALID", value)
    raw_parts = value.split("/")
    if any(part == ".." for part in raw_parts):
        raise WorktreeError("COLLECT_HANDOFF_PATH_PARENT_REF", value)
    parts = [part for part in raw_parts if part not in ("", ".")]
    if len(parts) != 3 or tuple(parts[:2]) != HANDOFF_DIR_PARTS:
        raise WorktreeError("COLLECT_HANDOFF_PATH_SHAPE_INVALID", value)
    match = HANDOFF_FILENAME_RE.fullmatch(parts[2])
    if match is None:
        raise WorktreeError("COLLECT_HANDOFF_FILENAME_INVALID", parts[2])
    if expected_issue is not None and int(match.group("issue")) != int(expected_issue):
        raise WorktreeError(
            "COLLECT_HANDOFF_ISSUE_MISMATCH",
            f"expected issue {expected_issue}; filename says {match.group('issue')}",
        )
    return "/".join(parts)

def validate_collect_dest(value: str) -> str:
    """``--into`` の「main worktree 相対」パスを検証する。

    書き先は ``tmp/_handoff/`` 配下に閉じる（回収物を任意の場所へ書けるようにしない）。
    ``tmp/_handoff/`` は ``dsv2 clean-tmp`` の保護対象なので、回収物が掃除で消えることもない。
    """
    if not isinstance(value, str) or not value:
        raise WorktreeError("COLLECT_DEST_PATH_EMPTY", repr(value))
    _reject_control_chars(value, "destination path")
    if value.startswith("~") or value.startswith("/"):
        raise WorktreeError("COLLECT_DEST_PATH_NOT_RELATIVE", value)
    if len(value) > 1 and value[1] == ":":
        raise WorktreeError("COLLECT_DEST_PATH_NOT_RELATIVE", value)
    if "\\" in value:
        raise WorktreeError("COLLECT_DEST_PATH_SEPARATOR_INVALID", value)
    raw_parts = value.split("/")
    if any(part == ".." for part in raw_parts):
        raise WorktreeError("COLLECT_DEST_PATH_PARENT_REF", value)
    parts = [part for part in raw_parts if part not in ("", ".")]
    if len(parts) < 3 or tuple(parts[:2]) != HANDOFF_DIR_PARTS:
        raise WorktreeError("COLLECT_DEST_PATH_SHAPE_INVALID", value)
    for part in parts[2:]:
        if not _SAFE_PATH_PART_RE.fullmatch(part):
            raise WorktreeError("COLLECT_DEST_PATH_SHAPE_INVALID", part)
    return "/".join(parts)
