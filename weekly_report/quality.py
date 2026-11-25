"""Measure CI and review evidence, and state limits of its interpretation."""

from collections import Counter

from .quantities import count, measured


def measure(period, github):
    workflow_data = github["ci"]
    workflows = workflow_data["rows"]
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
    reviews = github["reviews"]
    complete = github["pulls"]["rows"] is not None and all(data["rows"] is not None for data in reviews.values())
    in_period = [row for data in reviews.values() for row in data["rows"] or []
                 if period.contains(row["submitted_at"])]
    metrics["review_submissions"] = measured(
        len(in_period) if complete else None,
        "収集対象 PR の期間内レビュー投稿（観測時 open または期間内に close/merge）",
        "GitHub REST pulls/{number}/reviews",
        reason=None if complete else "PR またはレビュー投稿の取得範囲が不完全です",
        target_pr_numbers=sorted(reviews),
        observed_submissions=len(in_period),
    )
    return metrics
