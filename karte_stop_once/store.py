"""Session-local JSON state file with an exclusive lock and atomic replacement."""
import fcntl
import hashlib
import json
import os
import re
import tempfile
from contextlib import contextmanager
from pathlib import Path

_SESSION = re.compile(r"[A-Za-z0-9_-]{8,128}\Z", re.ASCII)


def state_file(root: Path, session: str) -> Path | None:
    if not isinstance(session, str) or not _SESSION.fullmatch(session):
        return None
    name = hashlib.sha256(session.encode("ascii")).hexdigest()
    return root / "tmp" / "_karte" / "stop-once" / (name + ".json")


@contextmanager
def locked(path: Path, create: bool):
    if not path.parent.is_dir():
        if not create:
            yield None
            return
        path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(str(path) + ".lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        value = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
        if not isinstance(value, dict):
            raise ValueError("invalid one-shot state")
        yield value
        temp = None
        try:
            with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent,
                                             prefix=".stop-", delete=False) as stream:
                temp = stream.name
                json.dump(value, stream, ensure_ascii=False)
            os.replace(temp, path)
        finally:
            if temp is not None and os.path.exists(temp):
                os.unlink(temp)
    finally:
        os.close(fd)
