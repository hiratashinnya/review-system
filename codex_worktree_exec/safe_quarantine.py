"""Fail-closed, non-deleting move with Git index serialization and inode checks."""
import os
import stat
import subprocess
from contextlib import contextmanager
from pathlib import Path


@contextmanager
def index_guard(root: Path):
    path = subprocess.run(["git", "-C", str(root), "rev-parse",
                           "--path-format=absolute", "--git-path", "index"],
                          check=True, capture_output=True, text=True).stdout.strip()
    lock = Path(path + ".lock")
    try:
        descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as error:
        raise ValueError("Git index is busy; recovery refused") from error
    try:
        yield
    finally:
        os.close(descriptor)
        lock.unlink()


def _untracked(root: Path, relative: Path) -> bool:
    data = subprocess.run(["git", "-C", str(root), "ls-files", "--others",
                           "-z", "--", relative.as_posix()],
                          check=True, capture_output=True).stdout
    return relative.as_posix().encode() in data.split(b"\0")


def _signature(info) -> tuple:
    return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_mode


@contextmanager
def _parent(root: Path, parts: tuple):
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    descriptors = [os.open(root, flags)]
    try:
        for part in parts:
            descriptors.append(os.open(part, flags, dir_fd=descriptors[-1]))
        yield descriptors[-1]
    finally:
        for descriptor in reversed(descriptors):
            os.close(descriptor)


def move_checked(root: Path, relative: Path, destination: Path, allowed) -> None:
    """Call while holding index_guard. Never unlink moved owner content."""
    if (relative.is_absolute() or ".." in relative.parts
            or not _untracked(root, relative) or not allowed(root, relative)):
        raise ValueError(f"no longer approved as untracked candidate: {relative}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with _parent(root, relative.parts[:-1]) as parent_fd:
        name = relative.name
        source_fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=parent_fd)
        try:
            expected = _signature(os.fstat(source_fd))
            if not stat.S_ISREG(expected[-1]):
                raise ValueError(f"nonregular candidate: {relative}")
            if _signature(os.stat(name, dir_fd=parent_fd, follow_symlinks=False)) != expected:
                raise ValueError(f"candidate changed before move: {relative}")
            os.rename(name, destination, src_dir_fd=parent_fd)
            try:
                actual = _signature(os.stat(destination, follow_symlinks=False))
                parent = os.stat(root.joinpath(*relative.parts[:-1]), follow_symlinks=False)
                connected = (parent.st_dev, parent.st_ino) == (
                    os.fstat(parent_fd).st_dev, os.fstat(parent_fd).st_ino)
                if actual == expected and _signature(os.fstat(source_fd)) == expected and connected:
                    return
            except FileNotFoundError:
                pass
            if not os.path.lexists(root / relative):
                os.rename(destination, name, dst_dir_fd=parent_fd)
            raise ValueError(f"candidate changed during move; inspect {relative} and {destination}")
        finally:
            os.close(source_fd)
