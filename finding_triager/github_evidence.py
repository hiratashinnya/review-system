"""Read Issue and PR evidence from the checkout's GitHub origin at an exact head."""

import json
import re
import subprocess
from pathlib import Path

from issue_start.gate_git import _canonical_github_repository


def _run(root, *argv):
    return subprocess.run(argv, cwd=root, check=True, capture_output=True, text=True,
                          timeout=30).stdout


def _read(root, repository, issue, pr):
    issue_data = json.loads(_run(root, "gh", "api", f"repos/{repository}/issues/{issue}"))
    pr_data = json.loads(_run(root, "gh", "api", f"repos/{repository}/pulls/{pr}"))
    return issue_data, pr_data


def github_evidence(root: Path, issue: int, pr: int, target_oid: str) -> dict:
    """Verify same-repository PR head and return Issue body and full local diff.

    A trusted caller chooses the PR; neither PR association nor owner approval is
    inferred from a mention. Existing approval validation is a separate gate.
    """
    root = Path(root).resolve(strict=True)
    if (type(issue) is not int or issue < 1 or type(pr) is not int or pr < 1
            or not isinstance(target_oid, str) or not re.fullmatch(r"[0-9a-f]{40}", target_oid)):
        raise ValueError("invalid Issue, PR, or target OID")
    repository = _canonical_github_repository(_run(root, "git", "remote", "get-url", "origin").strip())
    first_issue, first_pr = _read(root, repository, issue, pr)
    if (first_issue.get("number") != issue or "pull_request" in first_issue
            or not isinstance(first_issue.get("body"), str) or not first_issue["body"].strip()):
        raise ValueError("invalid Issue response")
    try:
        head, base = first_pr["head"], first_pr["base"]
        base_oid = base["sha"]
        if (first_pr["number"] != pr or first_pr["state"] != "open"
                or head["repo"]["full_name"].casefold() != repository.casefold()
                or base["repo"]["full_name"].casefold() != repository.casefold()
                or head["sha"] != target_oid or not re.fullmatch(r"[0-9a-f]{40}", base_oid)):
            raise ValueError("PR target mismatch")
    except (KeyError, TypeError, AttributeError) as exc:
        raise ValueError("invalid PR response") from exc
    change = _run(root, "git", "diff", "--no-ext-diff", "--no-textconv", base_oid + "..." + target_oid, "--")
    second_issue, second_pr = _read(root, repository, issue, pr)
    if (first_issue != second_issue or first_pr != second_pr):
        raise ValueError("Issue or PR changed during capture")
    return {"repository": repository, "issue": issue, "pr": pr, "target_oid": target_oid,
            "base_oid": base_oid, "issue_body": first_issue["body"], "change": change}
