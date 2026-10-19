"""Locate and safely read handoffs; write receipts within the pinned handoff directory."""
from __future__ import annotations

import json
import os
import re
import stat
from pathlib import Path

AGENT_TYPE = "gh-create-issue"
HANDOFF_DIR_REL = "tmp/_handoff"
MAX_DISPLAY_BYTES = 64 * 1024
RECEIPT_SUFFIX = ".receipt.json"
_NAME = r"gh-create-issue--[A-Za-z0-9][A-Za-z0-9._-]*\.md"
_HANDOFF_PATH = re.compile(re.escape(HANDOFF_DIR_REL) + r"/" + _NAME)
_HANDOFF_LINE = re.compile(r"HANDOFF:\s*(" + re.escape(HANDOFF_DIR_REL) + r"/" + _NAME + r")")


def find_handoff_rel(text: str) -> str | None:
    matches = _HANDOFF_LINE.findall(text or "")
    return matches[-1] if matches else None


def _open_handoff_dir(project_root: Path) -> int:
    nofollow, directory = getattr(os, "O_NOFOLLOW", None), getattr(os, "O_DIRECTORY", None)
    if nofollow is None or directory is None:
        raise OSError("no-follow directory opens are unavailable")
    root_fd = os.open(project_root, os.O_RDONLY | directory)
    try:
        tmp_fd = os.open("tmp", os.O_RDONLY | directory | nofollow, dir_fd=root_fd)
    finally:
        os.close(root_fd)
    try:
        return os.open("_handoff", os.O_RDONLY | directory | nofollow, dir_fd=tmp_fd)
    finally:
        os.close(tmp_fd)


def _open_regular_handoff(project_root: Path, rel: str) -> int:
    if not _HANDOFF_PATH.fullmatch(rel):
        raise OSError("handoff path is outside the contract")
    dir_fd = _open_handoff_dir(project_root)
    try:
        fd = os.open(rel.rsplit("/", 1)[1], os.O_RDONLY | os.O_NOFOLLOW, dir_fd=dir_fd)
    finally:
        os.close(dir_fd)
    if not stat.S_ISREG(os.fstat(fd).st_mode):
        os.close(fd)
        raise OSError("handoff is not a regular file")
    return fd


def resolve_handoff(project_root: Path, rel: str) -> Path | None:
    try:
        fd = _open_regular_handoff(project_root, rel)
        os.close(fd)
    except (OSError, TypeError, ValueError):
        return None
    return project_root / rel


def read_for_display(project_root: Path, rel: str) -> tuple[str, bool] | None:
    try:
        fd = _open_regular_handoff(project_root, rel)
        with os.fdopen(fd, "rb") as stream:
            raw = stream.read(MAX_DISPLAY_BYTES + 1)
    except (OSError, TypeError, ValueError):
        return None
    truncated = len(raw) > MAX_DISPLAY_BYTES
    return raw[:MAX_DISPLAY_BYTES].decode("utf-8", errors="replace"), truncated


def write_receipt(project_root: Path, rel: str, *, status: str, reason: str | None = None) -> bool:
    if not _HANDOFF_PATH.fullmatch(rel) or not hasattr(os, "O_NOFOLLOW"):
        return False
    try:
        dir_fd = _open_handoff_dir(project_root)
    except OSError:
        return False
    try:
        fd = os.open(rel.rsplit("/", 1)[1] + RECEIPT_SUFFIX,
                     os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                     0o600, dir_fd=dir_fd)
    except OSError:
        os.close(dir_fd)
        return False
    os.close(dir_fd)
    if not stat.S_ISREG(os.fstat(fd).st_mode):
        os.close(fd)
        return False
    payload = {"status": status}
    if reason:
        payload["reason"] = reason
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(json.dumps(payload, ensure_ascii=False) + "\n")
    except OSError:
        return False
    return True
