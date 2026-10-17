"""TOML読書き。追跡データの削除・暗黙上書きを行わない。"""
import os
import tempfile
import tomllib
from pathlib import Path
from feedback_ledger.tomlwrite import dumps
from .model import normalize
from .schema import SPECS
from .placement import validate_placement
from .discovery import artifact_directories

DIRECTORIES = ("change_plan", "verification_design", "investigation_report", "test_design")


def load(repo):
    root = Path(repo).resolve()
    records = []
    for directory in artifact_directories(root, DIRECTORIES):
        for path in sorted(directory.glob("*.toml")):
            if path.is_symlink():
                raise ValueError(f"artifactがsymlink: {path}")
            data = normalize(tomllib.loads(path.read_text(encoding="utf-8")))
            validate_placement(path, data, root)
            records.append((data, path))
    return records


def write(path, raw):
    data = normalize(raw)
    target = Path(path)
    validate_placement(target, data)
    if any(part.is_symlink() for part in (target, *target.parents)):
        raise ValueError("artifact経路がsymlink")
    text = dumps(SPECS[data["artifact_type"]], data)
    if normalize(tomllib.loads(text)) != data:
        raise ValueError("canonical roundtripが不一致")
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(dir=target.parent, prefix=".envelope-")
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(text)
        os.link(temporary, target)
    finally:
        os.unlink(temporary)
    return target
