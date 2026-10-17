"""旧PR再レビューの客観的なGitHub・Git証拠を照合する。"""
from datetime import datetime
import json
from pathlib import PurePosixPath

from .gate_git import _canonical_github_repository, _git_output
from .policy_rollout import discover_policy_rollout



def validate_legacy_pr(raw, root, runner):
    """GitHub作成時刻とHEAD treeから新2.0工程の自己申告迂回を拒否する。"""
    def run(argv):
        return _git_output(argv, cwd=root, runner=runner, reason="ISSUE_START_PR_REREVIEW_INVALID")

    repository, oid, branch = raw["repository"], raw["expected_oid"], raw["branch_name"]
    origin = _canonical_github_repository(run(["git", "remote", "get-url", "origin"]).strip())
    if origin.casefold() != repository.casefold():
        raise ValueError("repository differs from origin")
    pr = json.loads(run(["gh", "api", f"repos/{repository}/pulls/{raw['pr']}"]))
    if (pr["number"] != raw["pr"] or pr["state"] != "open" or pr["merged"] is not False
            or pr["head"]["repo"]["full_name"].casefold() != repository.casefold()
            or pr["base"]["repo"]["full_name"].casefold() != repository.casefold()
            or pr["head"]["ref"] != branch or pr["head"]["sha"] != oid):
        raise ValueError("PR must be same-repository OPEN at exact branch/OID")
    rollout_oid, rollout_at = discover_policy_rollout(repository, root, runner)
    created = datetime.fromisoformat(pr["created_at"].replace("Z", "+00:00"))
    if created >= rollout_at:
        raise ValueError("PR was created after phase rollout")
    if run(["git", "diff", "--name-only", "HEAD"]).strip():
        raise ValueError("review checkout has tracked changes")
    ref = f"refs/heads/{branch}"
    if run(["git", "ls-remote", "--exit-code", f"https://github.com/{repository}.git", ref]).split() != [oid, ref]:
        raise ValueError("remote exact OID mismatch")
    run(["git", "fetch", "--no-tags", f"https://github.com/{repository}.git", ref])
    if run(["git", "rev-parse", "FETCH_HEAD"]).strip() != oid:
        raise ValueError("PR changed during fetch")
    manifest = json.loads(run(["git", "show", f"{oid}:issue_start/managed-entrypoints-v2.json"]))
    if manifest.get("policy_version") != "issue-start/1.0":
        raise ValueError("new-policy PR requires normal phase approval")
    ancestors = run(["git", "rev-list", oid]).splitlines()
    if rollout_oid in ancestors:
        raise ValueError("phase rollout ancestor requires normal phase approval")
    names = run(["git", "ls-tree", "-r", "--name-only", oid]).splitlines()
    for name in names:
        path = PurePosixPath(name)
        if (path.suffix == ".toml" and path.parent.name in
                {"change_plan", "verification_design", "test_design"}):
            raise ValueError("phase artifacts require normal phase approval")
