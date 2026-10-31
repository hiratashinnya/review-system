"""取り込み merge commit の確定と、親列 [元 HEAD, base] の検証。"""

from .base_error import require
from .base_git import git, merge_head, output


def commit_resolution(workspace, record):
    request = record["request"]
    git(workspace, "commit", "--no-gpg-sign", "--no-verify", "-m",
        f"Integrate PR #{request['pr']} base into its head")
    oid = output(workspace, "rev-parse", "HEAD")
    parents = output(workspace, "rev-list", "--parents", "-n", "1", "HEAD").split()[1:]
    require(parents == [record["original_head"], request["base"]]
            and merge_head(workspace) is None, "BASE_COMMIT_PARENTS_MISMATCH")
    return {"oid": oid, "parents": parents, "tree": output(workspace, "rev-parse", "HEAD^{tree}")}
