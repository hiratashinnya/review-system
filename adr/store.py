"""ADR の安全な読書きと canonical TOML。"""
import os
import tempfile
import tomllib
import unicodedata
import fcntl
from contextlib import contextmanager
from pathlib import Path
from feedback_ledger.tomlwrite import dumps
from .model import normalize
from .schema import ADR_SPEC


@contextmanager
def issue_lock(root, name=".file-issue.lock"):
    directory = Path(root)
    if directory.is_symlink():
        raise ValueError("ADR root が symlink")
    directory.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(directory / name, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        yield
    finally:
        os.close(descriptor)


def load(root):
    directory = Path(root)
    if directory.is_symlink():
        raise ValueError("ADR root が symlink")
    records = {}
    for path in sorted(directory.glob("*.toml")):
        if path.is_symlink():
            raise ValueError(f"ADR が symlink: {path}")
        data = normalize(tomllib.loads(path.read_text(encoding="utf-8")))
        if path.name != data["id"] + ".toml":
            raise ValueError(f"ファイル名と id が不一致: {path}")
        key = unicodedata.normalize("NFKC", data["id"]).casefold()
        if key in records:
            raise ValueError("ADR id が互換正規化後に衝突")
        records[key] = (data, path)
    return list(records.values())


def write(root, raw, *, replace=False):
    with issue_lock(root, ".write.lock"):
        return _write_locked(root, raw, replace=replace)


def _write_locked(root, raw, *, replace=False):
    data = normalize(raw)
    directory = Path(root)
    if directory.is_symlink():
        raise ValueError("ADR root が symlink")
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / (data["id"] + ".toml")
    if target.is_symlink():
        raise ValueError("ADR target が symlink")
    key = unicodedata.normalize("NFKC", data["id"]).casefold()
    for other, path in load(directory):
        if unicodedata.normalize("NFKC", other["id"]).casefold() == key:
            if not replace or path != target:
                raise ValueError("既存 ADR の上書きは禁止")
    text = dumps(ADR_SPEC, data)
    if normalize(tomllib.loads(text)) != data:
        raise ValueError("canonical roundtrip が不一致")
    descriptor, temporary = tempfile.mkstemp(dir=directory, prefix=".adr-")
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(text)
        if replace:
            os.replace(temporary, target)
        else:
            os.link(temporary, target)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return target
