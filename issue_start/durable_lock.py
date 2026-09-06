"""Crash-safe advisory lock shared by all durable worktree-ledger writers."""

from __future__ import annotations

import fcntl
import json
import os
import re
import secrets
import stat
from pathlib import Path
from typing import Callable, Mapping


_HEX32 = re.compile(r"^[0-9a-f]{32}$")


class DurableLockError(RuntimeError):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


def _process_start_token(pid: int) -> str | None:
    try:
        text = Path(f"/proc/{pid}/stat").read_text(encoding="utf-8")
        token = text[text.rfind(")") + 2 :].split()[19]
    except (OSError, IndexError):
        return None
    return token if token.isdigit() else None


def _owner() -> dict[str, object]:
    token = _process_start_token(os.getpid())
    if token is None:
        raise DurableLockError("LOCK_PROCESS_TOKEN_UNAVAILABLE")
    return {
        "version": 1,
        "pid": os.getpid(),
        "process_start_token": token,
        "nonce": secrets.token_hex(16),
    }


def _validate_stale_owner(value: Mapping[str, object]) -> None:
    if (
        set(value) != {"version", "pid", "process_start_token", "nonce"}
        or value.get("version") != 1
        or not isinstance(value.get("pid"), int)
        or isinstance(value.get("pid"), bool)
        or value["pid"] <= 0
        or not isinstance(value.get("process_start_token"), str)
        or not value["process_start_token"].isdigit()
        or not isinstance(value.get("nonce"), str)
        or _HEX32.fullmatch(value["nonce"]) is None
    ):
        raise DurableLockError("LOCK_METADATA_TAMPERED")
    actual = _process_start_token(value["pid"])
    if actual is None:
        return
    if actual != value["process_start_token"]:
        raise DurableLockError("LOCK_PID_REUSED")
    raise DurableLockError("LOCK_OWNER_INCONSISTENT")


def acquire(
    path: Path,
    *,
    attempts: int,
    interval: float,
    sleep: Callable[[float], None],
) -> int:
    """Acquire a persistent-inode flock; only a kernel-released dead owner is recovered."""

    try:
        descriptor = os.open(
            path,
            os.O_CREAT | os.O_RDWR | os.O_CLOEXEC | getattr(os, "O_NOFOLLOW", 0),
            0o600,
        )
    except OSError as exc:
        raise DurableLockError("LOCK_PATH_TAMPERED") from exc
    try:
        metadata = os.fstat(descriptor)
        if (
            not stat.S_ISREG(metadata.st_mode)
            or metadata.st_uid != os.geteuid()
            or metadata.st_nlink != 1
            or stat.S_IMODE(metadata.st_mode) != 0o600
        ):
            raise DurableLockError("LOCK_PATH_TAMPERED")
        for index in range(max(1, attempts)):
            try:
                fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if index == max(1, attempts) - 1:
                    raise DurableLockError("LOCK_TIMEOUT")
                sleep(interval)
        os.lseek(descriptor, 0, os.SEEK_SET)
        prior = os.read(descriptor, 4096)
        if prior.strip():
            try:
                value = json.loads(prior)
            except json.JSONDecodeError as exc:
                raise DurableLockError("LOCK_METADATA_TAMPERED") from exc
            if not isinstance(value, dict):
                raise DurableLockError("LOCK_METADATA_TAMPERED")
            _validate_stale_owner(value)
        payload = json.dumps(_owner(), sort_keys=True, separators=(",", ":")).encode()
        os.ftruncate(descriptor, 0)
        os.lseek(descriptor, 0, os.SEEK_SET)
        os.write(descriptor, payload)
        os.fsync(descriptor)
        return descriptor
    except BaseException:
        try:
            fcntl.flock(descriptor, fcntl.LOCK_UN)
        except OSError:
            pass
        os.close(descriptor)
        raise


def release(descriptor: int) -> None:
    os.ftruncate(descriptor, 0)
    os.fsync(descriptor)
    fcntl.flock(descriptor, fcntl.LOCK_UN)
    os.close(descriptor)
