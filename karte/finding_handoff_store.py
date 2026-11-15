"""観測後の再検査と短いロック区間での台帳書込。"""
from . import model, owner_decision, paths
from .errors import KarteNotFound, KarteUsageError
from .finding_handoff_errors import FindingHandoffError
from .finding_handoff_preview import digest
from .karte_loader import load_karte


def snapshot(finding):
    return (digest(finding), finding.deferred_to, finding.status, finding.disposition, finding.handoff)


def store(repo_root, issue, finding_id, observed, record):
    try:
        with paths.writer_lock(repo_root):
            path, karte = load_karte(repo_root, issue)
            current = karte.finding(finding_id)
            try:
                unchanged = current is not None and snapshot(current) == observed
            except KarteUsageError:
                unchanged = False
            if not unchanged:
                raise FindingHandoffError("changed", "観測後に finding が変わった。再実行すること")
            current.handoff = record
            owner_decision.write_karte(path, karte)
    except (OSError, KarteNotFound, paths.KartePathError, model.KarteFormatError) as exc:
        raise FindingHandoffError("store", f"台帳を書き込めません: {exc}") from exc
