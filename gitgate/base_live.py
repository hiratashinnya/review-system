"""Verify same-repository OPEN PR and exact freshly fetched head/base evidence."""

from blocker_gate.auth import resolve_github_token
from branch_source.policy import GitHubBranchClient, validate_branch_ref
from .base_error import require
from .base_git import git, output


def default_api():
    return GitHubBranchClient(resolve_github_token())


def verify_live(workspace, request, binding, api):
    repository = request["repository"]
    require(repository == binding["repository"], "BASE_REPOSITORY_MISMATCH")
    pull = api.pull_request(repository, request["pr"])
    require(isinstance(pull, dict) and pull.get("state") == "open"
            and pull.get("number") == request["pr"], "BASE_PR_NOT_OPEN")
    head, base = pull.get("head", {}), pull.get("base", {})
    require(isinstance(head, dict) and isinstance(base, dict)
            and isinstance(head.get("repo"), dict) and isinstance(base.get("repo"), dict),
            "BASE_API_PARTIAL_RESPONSE")
    require(head.get("repo", {}).get("full_name") == repository
            and base.get("repo", {}).get("full_name") == repository,
            "BASE_FORK_OR_REPOSITORY_MISMATCH")
    require(head.get("sha") == request["head"] and base.get("sha") == request["base"],
            "BASE_LIVE_OID_MISMATCH")
    head_ref = validate_branch_ref(head.get("ref", ""), "BASE_HEAD_REF_INVALID")
    base_ref = validate_branch_ref(base.get("ref", ""), "BASE_BASE_REF_INVALID")
    require(head_ref == binding["branch"] and head_ref != base_ref,
            "BASE_HEAD_BRANCH_MISMATCH")
    metadata = api.repository(repository)
    require(isinstance(metadata, dict) and isinstance(metadata.get("default_branch"), str),
            "BASE_API_PARTIAL_RESPONSE")
    require(head_ref != metadata["default_branch"], "BASE_DEFAULT_BRANCH_DENIED")
    git(workspace, "fetch", "--no-tags", "origin",
        f"+refs/heads/{head_ref}:refs/remotes/origin/{head_ref}",
        f"+refs/heads/{base_ref}:refs/remotes/origin/{base_ref}")
    require(output(workspace, "rev-parse", f"refs/remotes/origin/{head_ref}") == request["head"]
            and output(workspace, "rev-parse", f"refs/remotes/origin/{base_ref}") == request["base"],
            "BASE_FETCH_OID_MISMATCH")
    fresh = api.pull_request(repository, request["pr"])
    evidence = lambda value: (value.get("number"), value.get("state"),
                              value.get("head"), value.get("base")) if isinstance(value, dict) else None
    require(evidence(fresh) == evidence(pull),
            "BASE_PR_CHANGED_DURING_FETCH")
    return base_ref
