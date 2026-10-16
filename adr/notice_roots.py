"""CLI が観測した書込 root の再構築可能な通知索引。"""
import hashlib
import json
import os
import tempfile
from pathlib import Path

PREFIX = "ADR-WRITE-ROOT: "


def workspace(path):
    directory = Path(path).resolve()
    return next((parent for parent in (directory, *directory.parents)
                 if (parent / ".git").exists()), directory)


def _directory(repo, *, create=False):
    directory = workspace(repo)
    for name in ("tmp", "_adr-notify"):
        directory = directory / name
        if directory.is_symlink():
            raise ValueError("ADR 通知索引が symlink")
        if create:
            directory.mkdir(exist_ok=True)
    return directory


def register_root(root, repo):
    absolute = str(Path(root).resolve())
    directory = _directory(repo, create=True)
    key = hashlib.sha256(absolute.encode()).hexdigest()
    descriptor, temporary = tempfile.mkstemp(dir=directory, prefix=".root-")
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(absolute)
        os.replace(temporary, directory / (key + ".root"))
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    print(PREFIX + json.dumps(absolute, ensure_ascii=False), flush=True)


def registered_roots(repo):
    roots = set()
    for path in _directory(repo).glob("*.root"):
        if path.is_symlink():
            raise ValueError("ADR 通知索引が symlink")
        absolute = path.read_text(encoding="utf-8")
        key = hashlib.sha256(absolute.encode()).hexdigest()
        if path.stem == key and Path(absolute).is_absolute():
            roots.add(Path(absolute))
    return roots


def response_roots(value):
    if isinstance(value, dict):
        return set().union(*(response_roots(item) for item in value.values()), set())
    if isinstance(value, list):
        return set().union(*(response_roots(item) for item in value), set())
    roots = set()
    if isinstance(value, str):
        for line in value.splitlines():
            if line.startswith(PREFIX):
                try:
                    absolute = json.loads(line[len(PREFIX):])
                    if isinstance(absolute, str) and Path(absolute).is_absolute():
                        roots.add(Path(absolute))
                except ValueError:
                    pass
    return roots
