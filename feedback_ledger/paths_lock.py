"""安定した lock file で CLI の書込みを直列化する。"""

from contextlib import contextmanager
import fcntl
import os
import stat

from .paths_guard import FeedbackPathError
from .paths_layout import feedback_dir

LOCK_FILENAME = ".writer.lock"


@contextmanager
def writer_lock(root):
    """呼出し側の書込み処理が終わるまで排他 lock を保持する。"""
    directory = feedback_dir(root, create=True)
    handle = os.open(
        directory / LOCK_FILENAME,
        os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW | os.O_CLOEXEC,
        0o600,
    )
    try:
        metadata = os.fstat(handle)
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
            raise FeedbackPathError("writer lock は単一の通常ファイルでなければならない")
        fcntl.flock(handle, fcntl.LOCK_EX)
        yield
    finally:
        os.close(handle)
