"""live PR 情報と fresh fetch で、取り込み先が PR head・取り込み元がその PR base であることを確かめる。"""

from urllib.parse import quote

from blocker_gate.auth import resolve_github_token
from branch_source.policy import GitHubBranchClient, validate_branch_ref
from .base_error import require
from .base_git import git, output


def default_api():
    return BaseGitHubClient(resolve_github_token())


class BaseGitHubClient(GitHubBranchClient):
    def branch(self, repository, name):
        return self._get(f"/repos/{repository}/branches/{quote(name, safe='')}")


def pull_evidence(api, request):
    pull = api.pull_request(request["repository"], request["pr"])
    require(isinstance(pull, dict) and pull.get("state") == "open"
            and pull.get("number") == request["pr"], "BASE_PR_NOT_OPEN")
    head, base = pull.get("head", {}), pull.get("base", {})
    require(isinstance(head, dict) and isinstance(base, dict)
            and isinstance(head.get("repo"), dict) and isinstance(base.get("repo"), dict),
            "BASE_API_PARTIAL_RESPONSE")
    return pull, head, base


def verify_live(workspace, request, binding, api, expected_base_ref=None):
    repository = request["repository"]
    require(repository == binding["repository"], "BASE_REPOSITORY_MISMATCH")
    pull, head, base = pull_evidence(api, request)
    require(head["repo"].get("full_name") == repository
            and base["repo"].get("full_name") == repository,
            "BASE_FORK_OR_REPOSITORY_MISMATCH")
    require(head.get("sha") == request["head"], "BASE_LIVE_OID_MISMATCH")
    head_ref = validate_branch_ref(head.get("ref", ""), "BASE_HEAD_REF_INVALID")
    base_ref = validate_branch_ref(base.get("ref", ""), "BASE_BASE_REF_INVALID")
    require(expected_base_ref is None or base_ref == expected_base_ref,
            "BASE_BASE_REF_CHANGED")
    require(head_ref == binding["branch"] and head_ref != base_ref,
            "BASE_HEAD_BRANCH_MISMATCH")
    metadata = api.repository(repository)
    require(isinstance(metadata, dict) and isinstance(metadata.get("default_branch"), str),
            "BASE_API_PARTIAL_RESPONSE")
    require(head_ref != metadata["default_branch"], "BASE_DEFAULT_BRANCH_DENIED")
    require_branch_tip(api, repository, base_ref, request["base"])
    git(workspace, "fetch", "--no-tags", "origin",
        f"+refs/heads/{head_ref}:refs/remotes/origin/{head_ref}",
        f"+refs/heads/{base_ref}:refs/remotes/origin/{base_ref}")
    require(output(workspace, "rev-parse", f"refs/remotes/origin/{head_ref}") == request["head"]
            and output(workspace, "rev-parse", f"refs/remotes/origin/{base_ref}") == request["base"],
            "BASE_FETCH_OID_MISMATCH")
    require(pull_evidence(api, request)[0] == pull, "BASE_PR_CHANGED_DURING_FETCH")
    require_branch_tip(api, repository, base_ref, request["base"])
    return base_ref


def require_branch_tip(api, repository, base_ref, expected):
    branch = api.branch(repository, base_ref)
    require(isinstance(branch, dict) and branch.get("name") == base_ref
            and isinstance(branch.get("commit"), dict)
            and branch["commit"].get("sha") == expected, "BASE_LIVE_OID_MISMATCH")
