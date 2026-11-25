"""Qualify collected pull file sets with stable base and head objects."""

from .gh_consistency import pull_observation_reason

FILES_API_CAP = 3000


def verify_file_sets(files, pulls, consistency):
    return {
        pull["number"]: _verify(pull, files[pull["number"]], consistency)
        for pull in pulls if pull["number"] in files
    }


def _verify(pull, dataset, consistency):
    head_sha, base_sha = pull["head_sha"], pull["base_sha"]
    observation = {"head_sha": head_sha, "base_sha": base_sha}
    rows = dataset["rows"]
    reason = dataset["reason"] or pull_observation_reason(consistency, pull["number"], include_base_sha=True)
    if reason is None and (head_sha is None or base_sha is None):
        reason = "PR の基点または HEAD の SHA を確定できません"
    if reason is None and rows is not None:
        if len(rows) >= FILES_API_CAP:
            reason = "PR 変更パスの GitHub API 上限に達しました"
        elif pull["changed_files"] is not None and len(rows) != pull["changed_files"]:
            reason = "PR の変更ファイル数と取得したパスの数が一致しません"
    return {**dataset, **observation, "rows": None if reason else rows, "reason": reason}
