"""Verify the tested tree and complete parent vector of a dedicated merge commit."""

from .base_error import require
from .base_git import git, merge_head, output
from .base_snapshot import snapshot


def commit_resolution(workspace, operation, tested):
    require(snapshot(workspace) == tested, "BASE_COMMIT_CONTENT_CAS_MISMATCH")
    tree = output(workspace, "write-tree")
    git(workspace, "commit", "--no-gpg-sign", "-m",
        f"Integrate PR #{operation['request']['pr']} base into its head [AI issue-fixer]")
    oid = output(workspace, "rev-parse", "HEAD")
    parents = output(workspace, "rev-list", "--parents", "-n", "1", "HEAD").split()[1:]
    require(parents == [operation["original_head"], operation["request"]["base"]],
            "BASE_COMMIT_PARENTS_MISMATCH")
    require(output(workspace, "rev-parse", "HEAD^{tree}") == tree
            and merge_head(workspace) is None, "BASE_COMMIT_TREE_MISMATCH")
    after = snapshot(workspace)
    require(not after["status"], "BASE_COMMIT_DIRTY_STOP")
    return {"oid": oid, "parents": parents, "tree": tree, "after": after}
