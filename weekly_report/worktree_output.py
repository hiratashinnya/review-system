"""Validate report destinations against Git worktrees before any output write."""

import os
from pathlib import Path
from tempfile import mkdtemp

from .git_source import read_git


def protected_paths(root):
    listing = read_git(root, "worktree", "list", "--porcelain", "-z")
    main_record = listing.split("\0\0", 1)[0].split("\0")
    worktrees = [Path(field.removeprefix("worktree ")).resolve()
                 for field in listing.split("\0") if field.startswith("worktree ")]
    if not worktrees:
        raise ValueError("Git 作業ツリーを特定できません")
    common = read_git(root, "rev-parse", "--path-format=absolute", "--git-common-dir")
    admin = read_git(root, "rev-parse", "--absolute-git-dir")
    if not common or not admin:
        raise ValueError("Git 管理領域を特定できません")
    common_dir, admin_dir = Path(common).resolve(), Path(admin).resolve()
    if worktrees[0] == common_dir and "bare" not in main_record and admin_dir != common_dir:
        raise ValueError("主作業ツリーが Git 管理領域と別にあり、所在を確認できません")
    return [root.resolve(), common_dir, admin_dir, *worktrees]


def _require_external(path, protected):
    if any(path.is_relative_to(directory) for directory in protected):
        raise ValueError("出力先は全作業ツリーと Git 管理領域の外を指定してください")


def _temporary_parent():
    for variable in ("TMPDIR", "TEMP", "TMP"):
        configured = os.environ.get(variable)
        if configured:
            return Path(configured).resolve()
    if os.name == "nt":
        return (Path(os.environ.get("SystemRoot", r"C:\Windows")) / "Temp").resolve()
    return Path("/tmp").resolve()


def destination(location, root):
    protected = protected_paths(root)
    if location is None:
        parent = _temporary_parent()
        _require_external(parent, protected)
        return Path(mkdtemp(prefix="weekly-report-", dir=parent))
    requested = Path(location).absolute()
    target = requested.parent.resolve() / requested.name
    _require_external(target.resolve(), protected)
    target.mkdir()
    return target
