"""Measure CI and review evidence, and state limits of its interpretation."""

from collections import Counter, defaultdict

from .gh_details import review_target
from .gh_pr_evidence import verified_heads
from .quantities import count, measured


def measure(period, github):
    workflow_data = github["ci"]
    workflows = None if workflow_data["rows"] is None else [
        row for row in workflow_data["rows"] if period.contains(row["created_at"])
    ]
    metrics = {
        "workflow_runs": count(workflows, "期間内に作成された GitHub Actions run（取得時の状態）",
                               workflow_data),
        "review_real_findings": measured(
            None, "カルテで実害ありと判定されたレビュー指摘", "karte/README.md",
            reason="リポジトリ全体の網羅的なカルテ原本を取得できません",
        ),
        "review_retries": measured(
            None, "独立レビューの再実施ラウンド数", "karte/README.md",
            reason="GitHub のレビュー投稿はカルテの round と対応づけられません",
        ),
        "review_repeat_rate": measured(
            None, "再指摘率", "karte/README.md",
            reason="期間を覆う同一 finding ID の履歴と分母を確定できません",
        ),
        "safety_incidents": measured(
            None, "安全機構の不具合発生・解消", "GitHub Issues / Actions",
            reason="安全機構の実害発生と解消を網羅的に識別する台帳・判定条件を取得できません",
        ),
        "autonomy": measured(
            None, "オーナー介入・自律完遂", "GitHub review / .ai/feedback",
            reason="人手介入を含めた全実行の分母が観測できません",
        ),
    }
    if workflows is not None:
        workflow_counts = Counter(run["conclusion"] or run["status"] for run in workflows)
        metrics["workflow_runs"]["by_result"] = dict(sorted(workflow_counts.items()))
    reviews = _period_reviews(period, github)
    rows = [row for data in reviews.values() for row in data["rows"] or []]
    reason = None
    status = "measured"
    if github["pulls"]["rows"] is None or any(data["rows"] is None for data in reviews.values()):
        reason = "PR またはレビュー投稿の取得範囲が不完全です"
        status = "not_retrieved"
    elif any(row["state"] != "PENDING" and row["submitted_at"] is None for row in rows):
        reason = "投稿済みレビューの時刻に欠損があり、期間内の件数を確定できません"
        status = "not_measured"
    in_period = [row for row in rows if row["state"] != "PENDING" and period.contains(row["submitted_at"])]
    metrics["review_submissions"] = measured(
        len(in_period) if reason is None else None,
        "収集対象 PR の期間内レビュー投稿（観測時 open または期間内に close/merge）",
        "GitHub REST pulls/{number}/reviews",
        reason=reason, status=status,
        target_pr_numbers=sorted(reviews),
        observed_submissions=len(in_period),
    )
    return metrics


def _period_reviews(period, github):
    reviews = github["reviews"]
    return {pull["number"]: reviews.get(pull["number"], {"rows": None})
            for pull in github["pulls"]["rows"] or [] if review_target(pull, period)}


def matching_heads(github):
    """Identify evidence with a known SHA matching the observed PR head."""
    if "head_ci" in github:
        return verified_heads(github)
    if github["pulls"]["rows"] is None:
        return None
    runs = github["ci"]["rows"]
    runs_by_sha = defaultdict(list)
    for row in runs or []:
        if row["head_sha"] is not None:
            runs_by_sha[row["head_sha"]].append(row["id"])
    heads = {}
    for pull in github["pulls"]["rows"]:
        number, sha = pull["number"], pull["head_sha"]
        if number not in github["reviews"]:
            continue
        reviews = github["reviews"][number]["rows"]
        review_ids = None if sha is None or reviews is None else [
            row["id"] for row in reviews if row["commit_id"] == sha
            and row["state"] != "PENDING" and row["submitted_at"] is not None
        ]
        heads[number] = {
            "head_sha": sha, "matching_workflow_run_ids": None if sha is None or runs is None else runs_by_sha[sha],
            "matching_review_ids": review_ids,
        }
    return heads
