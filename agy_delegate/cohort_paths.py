"""passwd home から固定 cohort directory を記述子で辿る。"""

import hashlib
import os
import pwd
import stat
from contextlib import ExitStack, contextmanager
from pathlib import Path

from .image_source import held_directory


def workspace_id(workspace: Path) -> str:
    """WSL canonical absolute workspace を index 名用 hash へ変換する。"""
    try:
        if not workspace.is_absolute() or workspace != workspace.resolve(strict=True):
            raise ValueError("cohort_workspace_invalid")
        if not workspace.is_dir():
            raise ValueError("cohort_workspace_invalid")
    except OSError:
        raise ValueError("cohort_workspace_invalid") from None
    return hashlib.sha256(str(workspace).encode("utf-8")).hexdigest()


@contextmanager
def held_cohort_directory(*, create: bool = False):
    """ancestor symlink、異なる owner、不適切な mode を修正せず拒否する。"""
    home = Path(pwd.getpwuid(os.getuid()).pw_dir)
    if not home.is_absolute() or ".." in home.parts:
        raise ValueError("cohort_home_invalid")
    home_parts = home.parts[1:]
    with ExitStack() as stack:
        descriptor = stack.enter_context(held_directory("/", "cohort_directory_unavailable"))
        _check_directory(os.fstat(descriptor), "ancestor")
        components = [*home_parts, ".local", "state", "agy-delegate", "cohorts", "v1"]
        for position, component in enumerate(components):
            policy = ("ancestor" if position < len(home_parts) - 1 else
                      "shared" if position < len(home_parts) + 2 else "private")
            if create and position >= len(home_parts):
                try:
                    os.mkdir(component, mode=0o700, dir_fd=descriptor)
                    os.fsync(descriptor)
                except FileExistsError:
                    pass
            descriptor = stack.enter_context(held_directory(
                component, "cohort_directory_unavailable", dir_fd=descriptor))
            _check_directory(os.fstat(descriptor), policy)
        yield descriptor


def _check_directory(info, policy: str) -> None:
    owner = 0 if policy == "ancestor" else os.getuid()
    mode = stat.S_IMODE(info.st_mode)
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != owner:
        raise ValueError("cohort_directory_owner_invalid")
    if mode & 0o022 or (policy == "private" and mode != 0o700):
        raise ValueError("cohort_directory_mode_invalid")
