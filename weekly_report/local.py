"""Read-only observations from the worktree and existing ledgers."""

from collections import Counter
from dataclasses import asdict
from pathlib import Path
from maintainability_lint.baseline import load_baseline
from maintainability_lint.scanner import scan

from . import ledger_advisory, ledger_feedback
from .git_source import read_git
from .history import breakdown
from .quantities import measured

LINT_SOURCE = "maintainability_lint/baseline.json + maintainability_lint.scanner.scan"
LINT_DEFINITION = "現在の作業ツリーで baseline と照合した保守性警告・違反"


def resolve_root(repo):
    return Path(read_git(repo, "rev-parse", "--show-toplevel")).resolve()


def checkout(repo, base_ref):
    base_error = None
    try:
        base = read_git(repo, "rev-parse", "--verify", "--end-of-options", base_ref + "^{commit}")
    except ValueError:
        base = None
        base_error = "指定 ref をローカルで解決できません"
    return {
        "base_ref": base_ref, "base_sha": base, "base_reason": base_error,
        "checkout_sha": read_git(repo, "rev-parse", "--verify", "HEAD"),
        "checkout_dirty": bool(read_git(repo, "status", "--porcelain=v1")),
    }


def capture_maintainability(root):
    try:
        baseline = load_baseline(root / "maintainability_lint/baseline.json")
        result = scan(root, baseline)
        breakdown(baseline)
        return {"source": LINT_SOURCE, "baseline": baseline,
                "findings": [asdict(row) for row in result.findings], "reason": None}
    except (OSError, ValueError, SyntaxError, TypeError, AssertionError) as exc:
        return {"source": LINT_SOURCE, "baseline": None, "findings": None,
                "reason": f"スキャン不能 ({type(exc).__name__})"}


def measure_maintainability(evidence):
    baseline = evidence["baseline"]
    findings = evidence["findings"]
    source = evidence["source"]
    if findings is None or baseline is None:
        return measured(None, LINT_DEFINITION, source, reason=evidence["reason"], status="not_retrieved")
    by_status = {status: dict(Counter(row["rule"] for row in findings if row["status"] == status))
                 for status in ("accepted-debt", "violation")}
    return measured(sum(by_status["violation"].values()), LINT_DEFINITION, source,
                    baseline={"schema_version": baseline["schema_version"], "source": baseline["source"],
                              **breakdown(baseline)}, observed_by_status=by_status, findings=findings)


def maintainability(root):
    return measure_maintainability(capture_maintainability(root))


def owner_proposals(root):
    return ledger_feedback.measure(ledger_feedback.capture(root))["owner_pending_proposals"]


def advisory(root, period):
    return ledger_advisory.measure(period, ledger_advisory.capture(root))
