"""PR base ref verification; a stale remote version is never overwritten."""

import hashlib
import subprocess
import tomllib
from pathlib import Path

from .paths import LEDGER


def git(root: Path, *args: str) -> bytes:
    run = subprocess.run(["git", "-C", str(root), *args], capture_output=True,
                         check=False)
    if run.returncode:
        raise ValueError("git " + " ".join(args[:2]) + ": " +
                         run.stderr.decode("utf-8", "replace").strip())
    return run.stdout


def base_files(root: Path, ref: str) -> dict[str, bytes]:
    git(root, "rev-parse", "--verify", ref + "^{commit}")
    names = git(root, "ls-tree", "-r", "--name-only", ref, "--",
                LEDGER.as_posix()).decode("utf-8").splitlines()
    return {Path(name).stem: git(root, "show", ref + ":" + name)
            for name in names if name.endswith(".toml")}


def compare_to_base(root: Path, catalog: dict[str, dict],
                    ref: str) -> tuple[list[str], dict[str, dict]]:
    originals = base_files(root, ref)
    errors, other = [], {}
    for key, data in originals.items():
        if key not in catalog:
            other[key] = tomllib.loads(data.decode("utf-8"))
            continue
        path = LEDGER / (key + ".toml")
        local = (root / path).read_bytes()
        if local != data and catalog[key].get("base_sha256") != hashlib.sha256(data).hexdigest():
            errors.append(key + ": lost-update risk, base revision changed")
    for key, item in catalog.items():
        if key not in originals and item.get("base_sha256"):
            errors.append(key + ": created entry has unexpected base_sha256")
    return errors, other


def base_for_write(root: Path, ref: str, key: str,
                   local: bytes | None, previous: str) -> str:
    originals = base_files(root, ref)
    data = originals.get(key)
    if data is None:
        if previous:
            raise ValueError("entry has no base but declares previous checksum")
        return ""
    expected = hashlib.sha256(data).hexdigest()
    if local == data:
        return expected
    if previous != expected:
        raise ValueError("lost update: base changed since the local revision")
    return previous
