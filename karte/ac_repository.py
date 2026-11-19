"""Freeze GitHub host and repository together from the trusted checkout origin."""
import json
from pathlib import Path
import re
import subprocess
from urllib.parse import urlsplit

from . import paths
from .errors import KarteUsageError

_REPO = re.compile(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+\Z")
_HOST = re.compile(r"(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\.)+[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\Z")


def normalize(value):
    if not isinstance(value, str) or _REPO.fullmatch(value) is None:
        raise KarteUsageError("凍結repositoryはGitHubのowner/name形式が必要")
    return value.lower()


def normalize_host(value):
    if not isinstance(value, str) or len(value) > 253 or _HOST.fullmatch(value) is None:
        raise KarteUsageError("凍結GitHubホストが不正")
    return value.lower()


def checkout_origin(repo_root):
    """Read host/repo as one identity; never trust a write-target argument."""
    try:
        result = subprocess.run(
            ["git", "-C", str(Path(repo_root).resolve()), "remote", "get-url", "origin"],
            capture_output=True, text=True, timeout=5, check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode:
        return None
    raw = result.stdout.strip()
    try:
        scp = re.fullmatch(r"git@([^/:]+):([^?#]+)", raw)
        if scp:
            host, name = scp.groups()
        else:
            url = urlsplit(raw)
            if (url.scheme not in ("https", "ssh") or url.query or url.fragment
                    or url.username != ("git" if url.scheme == "ssh" else None)
                    or url.password is not None or url.port is not None):
                return None
            host, name = url.hostname, url.path.strip("/")
        if name.lower().endswith(".git"):
            name = name[:-4]
        return {"host": normalize_host(host), "repository": normalize(name)}
    except (KarteUsageError, ValueError):
        return None


def _record_path(snapshot, repo_root):
    return paths.resolve_within_repo(Path(str(snapshot) + ".repository.json"), repo_root)


def bind(repo_root, snapshot, identity):
    """Never allow rebinding an archived Issue snapshot to another origin."""
    content = json.dumps({"host": normalize_host(identity["host"]),
                          "repository": normalize(identity["repository"])}, sort_keys=True) + "\n"
    target = _record_path(snapshot, repo_root)
    if target.is_file():
        if paths.read_text(target) != content:
            raise KarteUsageError("同じAC原本へのoriginの再束縛を拒否")
    elif target.exists():
        raise KarteUsageError("AC原本のorigin束縛が通常ファイルでない")
    else:
        paths.write_text_atomic(target, content)
    if paths.read_text(target) != content:
        raise KarteUsageError("AC原本のorigin束縛を検証できない")


def frozen(repo_root, snapshot, *, required=False):
    target = _record_path(snapshot, repo_root)
    if not target.is_file():
        if required or target.exists():
            raise KarteUsageError("AC原本にtrusted GitHub origin束縛が無い")
        return None
    try:
        data = json.loads(paths.read_text(target))
    except (ValueError, RecursionError) as exc:
        raise KarteUsageError("AC原本のorigin束縛が壊れている") from exc
    if not isinstance(data, dict) or set(data) != {"host", "repository"}:
        raise KarteUsageError("AC原本のorigin束縛形式が不正")
    identity = {"host": normalize_host(data["host"]), "repository": normalize(data["repository"])}
    if checkout_origin(repo_root) != identity:
        raise KarteUsageError("AC原本と現在のGitHub checkoutのoriginが不一致")
    return identity
