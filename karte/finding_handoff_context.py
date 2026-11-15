"""申し送り対象と Issue の前提条件。"""
from . import finding_handoff_github as github
from . import finding_handoff_origin, repo_roots
from .errors import KarteUsageError
from .finding_handoff_target import normalize_target
from .karte_loader import load_karte
from .pointer_completion import resolve_issue


def load(args, repo_root):
    issue = resolve_issue(args, repo_root)
    return issue, load_karte(repo_root, issue)[1]


def origin():
    return finding_handoff_origin.get_origin(repo_roots.invoking_worktree())


def target_for(finding, target, repository):
    if finding.status != "open" or finding.disposition != "deferred" or finding.harm != "none":
        raise KarteUsageError("open・harm: none・disposition: deferred の finding が必要です")
    normalized = normalize_target(target, repository)
    if not normalized or normalize_target(finding.deferred_to, repository) != normalized:
        raise KarteUsageError("宛先が deferred_to と一致しないか自 repository の Issue ではありません")
    return normalized


def require_finding(karte, finding_id):
    finding = karte.finding(finding_id)
    if finding is None:
        raise KarteUsageError(f"台帳に無い finding ID: {finding_id}")
    return finding


def issue_status(target):
    issue = github.get_issue(target)
    if issue["state"] != "open":
        from .finding_handoff_errors import FindingHandoffError
        raise FindingHandoffError("closed", f"宛先 Issue は closed です（{issue['state_reason']}）")
    return issue
