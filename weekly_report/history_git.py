"""Capture the main first-parent history and its baseline file versions."""

import json
import re
import subprocess

from .git_source import read_git
from .period import parse_jst

BASELINE_PATH = "maintainability_lint/baseline.json"
MAIN_HISTORY_SOURCE = f"origin/main first-parent · {BASELINE_PATH}"
OID = re.compile(r"[0-9a-f]{40}\Z")


def _git(root, *args):
    return read_git(root, "--no-replace-objects", *args)


def _first_parent(root, main_sha):
    lines = _git(root, "log", "--first-parent", "--format=%H %cI", main_sha).splitlines()
    commits = []
    effective = None
    for line in reversed(lines):
        sha, time = line.split(" ", 1)
        stamp = parse_jst(time)
        if not OID.fullmatch(sha):
            raise ValueError("first-parent コミット SHA が不正")
        effective = stamp if effective is None else max(stamp, effective)
        commits.append({"sha": sha, "committed_at": stamp.isoformat(),
                        "effective_at": effective.isoformat()})
    if not commits or commits[-1]["sha"] != main_sha:
        raise ValueError("origin/main の first-parent 履歴が不完全")
    return commits


def _baseline_version(root, sha):
    try:
        entry = _git(root, "ls-tree", sha, "--", BASELINE_PATH)
        if not entry:
            return {"record": None, "reason": "対象コミットに baseline がありません", "absent": True}
        if not entry.startswith(("100644 blob ", "100755 blob ")):
            raise ValueError("baseline が通常ファイルではありません")
        parsed = json.loads(_git(root, "cat-file", "blob", f"{sha}:{BASELINE_PATH}"))
        return {"record": parsed, "reason": None, "absent": False}
    except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
        return {"record": None, "reason": f"履歴の baseline を読み取れませんでした ({type(exc).__name__})",
                "absent": False}


def capture(root, main_sha):
    """Read the pinned, local origin/main history without checking out old commits."""
    result = {"source": MAIN_HISTORY_SOURCE, "main_sha": main_sha, "commits": [],
              "versions": {}, "shallow": None, "reason": None}
    if not isinstance(main_sha, str) or not OID.fullmatch(main_sha):
        return result | {"reason": "origin/main の基準 SHA を取得できません"}
    try:
        commits = _first_parent(root, main_sha)
        shallow = _git(root, "rev-parse", "--is-shallow-repository")
        if shallow not in {"true", "false"}:
            raise ValueError("shallow 状態を確認できません")
        changed = set(_git(root, "log", "--first-parent", "--full-history", "--format=%H",
                           main_sha, "--", BASELINE_PATH).splitlines())
        if changed - {commit["sha"] for commit in commits}:
            raise ValueError("baseline 変更が first-parent の履歴外にあります")
        changed.add(commits[0]["sha"])
        return result | {"commits": commits, "shallow": shallow == "true",
                         "versions": {sha: _baseline_version(root, sha) for sha in sorted(changed)}}
    except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
        return result | {"reason": f"origin/main の履歴を取得できません ({type(exc).__name__})"}
