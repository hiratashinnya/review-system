"""Freeze an Issue review's GitHub repository from the trusted checkout."""
import json
from pathlib import Path
import re
import subprocess

from . import paths
from .errors import KarteUsageError

_REPO = re.compile(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+\Z")
_PREFIXES = ("https://github.com/", "git@github.com:", "ssh://git@github.com/")


def normalize(value):
    if not isinstance(value, str) or _REPO.fullmatch(value) is None:
        raise KarteUsageError("凍結repositoryはGitHubのowner/name形式が必要")
    return value.lower()


def checkout_repo(repo_root):
    """Use checkout origin, not the later caller-supplied write destination."""
    try:
        result = subprocess.run(
            ["git", "-C", str(Path(repo_root).resolve()), "remote", "get-url", "origin"],
            capture_output=True, text=True, timeout=5, check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode:
        return None
    url = result.stdout.strip()
    prefix = next((p for p in _PREFIXES if url.lower().startswith(p)), None)
    if prefix is None:
        return None
    name = url[len(prefix):].rstrip("/")
    if name.lower().endswith(".git"):
        name = name[:-4]
    return normalize(name) if _REPO.fullmatch(name) else None


def _record_path(snapshot, repo_root):
    return paths.resolve_within_repo(Path(str(snapshot) + ".repository.json"), repo_root)


def bind(repo_root, snapshot, repository):
    """Store origin identity immutably beside the content-hashed frozen body."""
    target = _record_path(snapshot, repo_root)
    content = json.dumps({"repository": normalize(repository)}, sort_keys=True) + "\n"
    if target.is_file():
        if paths.read_text(target) != content:
            raise KarteUsageError("同じAC原本へのrepositoryの再束縛を拒否")
    elif target.exists():
        raise KarteUsageError("AC原本のrepository束縛が通常ファイルでない")
    else:
        paths.write_text_atomic(target, content)
    if paths.read_text(target) != content:
        raise KarteUsageError("AC原本のrepository束縛を検証できない")


def frozen(repo_root, snapshot, *, required=False):
    """Missing or changed provenance always stops the owner write path."""
    target = _record_path(snapshot, repo_root)
    if not target.is_file():
        if required or target.exists():
            raise KarteUsageError("AC原本にtrusted repository束縛が無い")
        return None
    try:
        data = json.loads(paths.read_text(target))
    except (ValueError, RecursionError) as exc:
        raise KarteUsageError("AC原本のrepository束縛が壊れている") from exc
    if not isinstance(data, dict) or set(data) != {"repository"}:
        raise KarteUsageError("AC原本のrepository束縛形式が不正")
    repository = normalize(data["repository"])
    if checkout_repo(repo_root) != repository:
        raise KarteUsageError("AC原本と現在のGitHub checkoutのrepositoryが不一致")
    return repository
