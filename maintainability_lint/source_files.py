"""Issue #539 が対象とする Python 実装ファイルの列挙。"""

from pathlib import Path


SOURCE_ROOTS = (
    ".codex",
    "ai_layout",
    "asset_parity",
    "blocker_gate",
    "branch_source",
    "ci_anomaly_report",
    "defect_metrics",
    "feedback_ledger",
    "gitgate",
    "guidance_sync",
    "issue_start",
    "karte",
    "karte_notify",
    "maintainability_lint",
    "pr_merge_gate",
    "project_status_sync",
    "review_system",
    "time_fixture_lint",
)


def implementation_python_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for relative_root in SOURCE_ROOTS:
        source_root = root / relative_root
        if source_root.is_dir():
            files.extend(source_root.rglob("*.py"))
    return sorted(path for path in files if "__pycache__" not in path.parts)
