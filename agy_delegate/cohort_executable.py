"""校正済み実行fileを、版照会より前にbounded descriptorで照合する。"""

import hashlib
import os
import stat
from pathlib import Path


def executable_sha256(path: Path) -> str:
    """原binary値は公開せず、更新中/非regular/リンク/過大を拒否。"""
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(descriptor, "rb") as stream:
        before = os.fstat(stream.fileno())
        if not stat.S_ISREG(before.st_mode) or before.st_size > 268435456:
            raise ValueError("cohort_executable_invalid")
        digest = hashlib.sha256()
        read = 0
        for block in iter(lambda: stream.read(1048576), b""):
            read += len(block)
            if read > 268435456:
                raise ValueError("cohort_executable_invalid")
            digest.update(block)
        after = os.fstat(stream.fileno())
        fields = ("st_dev", "st_ino", "st_mode", "st_size", "st_mtime_ns", "st_ctime_ns")
        if any(getattr(before, key) != getattr(after, key) for key in fields):
            raise ValueError("cohort_executable_changed")
    return digest.hexdigest()
