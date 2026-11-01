"""固定 package 内の全 Python/PowerShell source を安定読取して束縛する。"""

import hashlib
import json
import os
import stat
from pathlib import Path

from .cohort_private_io import file_identity
from .image_source import FILE_FLAGS, held_directory

_PACKAGE_DIRECTORY = Path(__file__).parent
_MAX_SOURCE_BYTES = 1024 * 1024


def current_generator_sha256() -> str:
    """引数/環境のmanifestを受け取らず、固定source closureのhashだけを返す。"""
    try:
        with held_directory(_PACKAGE_DIRECTORY, "cohort_generator_unavailable") as descriptor:
            directory_before = file_identity(os.fstat(descriptor))
            names = _source_names(descriptor)
            records = {name: _read_source(descriptor, name) for name in names}
            if names != _source_names(descriptor):
                raise ValueError("cohort_generator_changed")
            for name, (_, identity) in records.items():
                current = os.stat(name, dir_fd=descriptor, follow_symlinks=False)
                if identity != file_identity(current):
                    raise ValueError("cohort_generator_changed")
            if directory_before != file_identity(os.fstat(descriptor)):
                raise ValueError("cohort_generator_changed")
        hashes = {name: digest for name, (digest, _) in records.items()}
        canonical = json.dumps(hashes, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(canonical).hexdigest()
    except OSError:
        raise ValueError("cohort_generator_unavailable") from None


def _source_names(descriptor: int) -> tuple[str, ...]:
    names = tuple(sorted(name for name in os.listdir(descriptor)
                         if Path(name).suffix in {".py", ".ps1"}))
    if not names:
        raise ValueError("cohort_generator_inventory_invalid")
    return names


def _read_source(directory_fd: int, name: str) -> tuple[str, tuple]:
    descriptor = os.open(name, FILE_FLAGS, dir_fd=directory_fd)
    with os.fdopen(descriptor, "rb") as stream:
        before = os.fstat(stream.fileno())
        if not stat.S_ISREG(before.st_mode):
            raise ValueError("cohort_generator_source_type_invalid")
        if before.st_size > _MAX_SOURCE_BYTES:
            raise ValueError("cohort_generator_source_too_large")
        content = stream.read(_MAX_SOURCE_BYTES + 1)
        after = os.fstat(stream.fileno())
        if len(content) > _MAX_SOURCE_BYTES:
            raise ValueError("cohort_generator_source_too_large")
        if file_identity(before) != file_identity(after) or len(content) != before.st_size:
            raise ValueError("cohort_generator_changed")
        return hashlib.sha256(content).hexdigest(), file_identity(after)
