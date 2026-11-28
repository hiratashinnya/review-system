"""Bind observed CI and reviews to both the PR identity and its observed head."""

from .gh_consistency import pull_observation_reason


def verified_heads(github):
    if github["pulls"]["rows"] is None:
        return None
    return {
        pull["number"]: _pr_evidence(pull, github)
        for pull in github["pulls"]["rows"] if pull["number"] in github["reviews"]
    }


def _pr_evidence(pull, github):
    number, sha = pull["number"], pull["head_sha"]
    stability = pull_observation_reason(github["consistency"]["pulls"], number)
    reason = stability or ("PR の HEAD SHA を確認できません" if sha is None else None)
    workflows, workflow_reason = _workflows(pull, github["head_ci"].get(sha), reason)
    review_data = github["reviews"][number]
    rows = review_data["rows"]
    review_reason = reason or review_data["reason"]
    if rows is not None and any(row["state"] != "PENDING" and (
        row["submitted_at"] is None or row["commit_id"] is None
    ) for row in rows):
        review_reason = review_reason or "一部レビューの投稿時刻または対象 SHA を取得できません"
    reviews = None
    if not reason and rows is not None:
        reviews = [row["id"] for row in rows if row["commit_id"] == sha
                   and row["state"] != "PENDING" and row["submitted_at"] is not None]
    return {"head_sha": sha, "matching_workflow_run_ids": workflows, "matching_review_ids": reviews,
            "workflow_scope": "Actions pull_request と PR ID・番号・対象リポジトリ ID・HEAD SHA の一致",
            "workflow_source": github["head_ci"][sha]["source"] if sha in github["head_ci"] else None,
            "workflow_reason": workflow_reason, "review_reason": review_reason}


def _workflows(pull, dataset, reason):
    if reason:
        return None, reason
    if pull["id"] is None or pull["base_repo_id"] is None:
        return None, "PR または対象リポジトリの識別子を取得できません"
    if dataset is None or dataset["rows"] is None:
        return None, dataset["reason"] if dataset else "対象 HEAD の Actions 証跡がありません"
    identity = {key: pull[key] for key in ("id", "number", "base_repo_id", "head_sha")}
    matches, unlinked = [], False
    for run in dataset["rows"]:
        if run["head_sha"] != pull["head_sha"] or run["event"] != "pull_request":
            unlinked = True
        elif not run["pull_requests"] or any(None in row.values() for row in run["pull_requests"]):
            unlinked = True
        if (run["head_sha"] == pull["head_sha"] and run["event"] == "pull_request"
                and identity in (run["pull_requests"] or [])):
            matches.append(run["id"])
    return matches if matches or not unlinked else None, (
        "一部の Actions run は対象 PR への関連を確定できません" if unlinked else None
    )
