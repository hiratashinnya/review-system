"""fresh defaultのfirst-parent履歴からpolicy 2導入点を導出する。"""
from datetime import datetime
import json

from .gate_git import _git_output
from .gate_support import _BRANCH, _OID

MANIFEST = "issue_start/managed-entrypoints-v2.json"


def discover_policy_rollout(repository, root, runner):
    """default未導入・取得不能・履歴不明では旧PR補助経路を有効にしない。"""
    def run(argv):
        return _git_output(argv, cwd=root, runner=runner, reason="ISSUE_START_PR_REREVIEW_INVALID")

    repo = json.loads(run(["gh", "api", f"repos/{repository}"]))
    branch = repo["default_branch"]
    if not isinstance(branch, str) or not _BRANCH.fullmatch(branch):
        raise ValueError("invalid trusted default branch")
    url, ref = f"https://github.com/{repository}.git", f"refs/heads/{branch}"
    remote = run(["git", "ls-remote", "--exit-code", url, ref]).split()
    if len(remote) != 2 or not _OID.fullmatch(remote[0]) or remote[1] != ref:
        raise ValueError("default remote OID unavailable")
    run(["git", "fetch", "--no-tags", url, ref])
    oid = run(["git", "rev-parse", "FETCH_HEAD"]).strip()
    if oid != remote[0]:
        raise ValueError("default changed during fetch")
    revisions = run(["git", "rev-list", "--first-parent", "--reverse", oid, "--", MANIFEST]).splitlines()
    previous, rollout = None, None
    for revision in revisions:
        exists = run(["git", "ls-tree", "--name-only", revision, "--", MANIFEST]).strip()
        if not exists:
            previous = None
            continue
        policy = json.loads(run(["git", "show", f"{revision}:{MANIFEST}"]))["policy_version"]
        if not isinstance(policy, str) or not policy.startswith("issue-start/"):
            raise ValueError("invalid default policy version")
        major = int(policy.removeprefix("issue-start/").split(".")[0])
        if major == 2 and previous == 1 and rollout is None:
            timestamp = run(["git", "show", "-s", "--format=%cI", revision]).strip()
            rollout = revision, datetime.fromisoformat(timestamp)
        previous = major
    if previous != 2 or rollout is None:
        raise ValueError("trusted default has no observable policy 1-to-2 rollout")
    return rollout
