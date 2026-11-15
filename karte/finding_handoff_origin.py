"""呼び出し元 worktree の origin を GitHub repository に変換する。"""

import re
import subprocess
from urllib.parse import urlsplit

from .finding_handoff_errors import FindingHandoffError
from .finding_handoff_target import REPO


def parse_origin(url):
    url = url.strip()
    scp = re.fullmatch(r"git@([^:]+):(.+)", url, re.IGNORECASE)
    if scp:
        host, path = scp.groups()
    else:
        try:
            parsed = urlsplit(url)
            if parsed.scheme.lower() not in ("https", "ssh") or parsed.query or parsed.fragment:
                raise ValueError
            if parsed.scheme.lower() == "ssh" and parsed.username != "git":
                raise ValueError
            if parsed.scheme.lower() == "https" and parsed.username is not None:
                raise ValueError
            if parsed.port is not None:
                raise ValueError
            host, path = parsed.hostname, parsed.path.removeprefix("/")
        except ValueError as exc:
            raise FindingHandoffError("origin_invalid", "origin URL を解析できません") from exc
    if not host:
        raise FindingHandoffError("origin_invalid", "origin URL を解析できません")
    if host.lower() != "github.com":
        raise FindingHandoffError("origin_host", "origin は github.com ではありません")
    if path.lower().endswith(".git"):
        path = path[:-4]
    if not re.fullmatch(REPO, path, re.ASCII) or any(part in (".", "..") for part in path.split("/")):
        raise FindingHandoffError("origin_invalid", "origin URL を解析できません")
    return path


def get_origin(worktree, run=None):
    run = run or subprocess.run
    try:
        result = run(["git", "remote", "get-url", "origin"], cwd=worktree, check=True,
                     capture_output=True, text=True, timeout=30, shell=False)
    except subprocess.CalledProcessError as exc:
        raise FindingHandoffError("origin_missing", "origin を取得できません") from exc
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        raise FindingHandoffError("origin_unavailable", "git を実行できません") from exc
    return parse_origin(result.stdout)
