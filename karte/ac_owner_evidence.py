"""Fail-close proof that a clean accepted round belongs to frozen Issue AC."""
from hashlib import sha256
from pathlib import Path

from . import ac_repository, ingest_receipt, karte_rounds, paths
from .ac_snapshot import digest, from_issue_body
from .ac_snapshot_archive import path_for_record
from .active_pointer import read_active
from .errors import KarteUsageError
from .karte_loader import load_karte
from .review_summary import parse_summary
from .status_payload import status_payload


def require_trusted_round(repo_root, issue, round_no, snapshot_source):
    """Never take AC judgments or a successful verdict from caller text."""
    issue = paths.validate_issue(issue)
    if type(round_no) is not int or round_no < 1:
        raise KarteUsageError("AC更新には正しいreview round番号が必要")
    _, ledger = load_karte(repo_root, issue)
    if ledger.issue != issue or karte_rounds.last_round(ledger) != round_no:
        raise KarteUsageError("AC更新のIssueまたは最新review roundが不一致")
    if status_payload(ledger, repo_root)["verdict"] != "clean":
        raise KarteUsageError("reviewがcleanではないためAC更新を拒否")
    active = read_active(repo_root, required=True)
    if (active.get("issue") != issue or active.get("round") != round_no
            or active.get("review_expect") is not None):
        raise KarteUsageError("reviewの進行ポインタと受理済みroundが不一致")
    rounds = [record for record in ledger.review_rounds if record.number == round_no]
    if len(rounds) != 1 or not rounds[0].source:
        raise KarteUsageError("受理済みreview原本のレシートが無い")
    original = ingest_receipt.original_path(repo_root, issue, round_no)
    source = str(original.relative_to(Path(repo_root).resolve())).replace("\\", "/")
    if rounds[0].source != source:
        raise KarteUsageError("review原本の参照先が不一致")
    report = paths.read_text(original)
    if sha256(report.encode("utf-8")).hexdigest() != rounds[0].digest:
        raise KarteUsageError("review原本のSHA-256が受理レシートと不一致")
    summary = parse_summary(report, issue)
    if summary is None:
        raise KarteUsageError("受理済みReview Summaryが存在しない")
    if not isinstance(snapshot_source, str):
        raise KarteUsageError("AC snapshot sourceが不正")
    snapshot = path_for_record(repo_root, issue, round_no, {"source": snapshot_source})
    identity = ac_repository.frozen(repo_root, snapshot, required=True)
    body = paths.read_text(snapshot)
    items = from_issue_body(body)
    if summary.ac_count != len(items) or summary.ac_snapshot_digest != digest(items):
        raise KarteUsageError("review判定とtrusted AC snapshotの件数・digestが不一致")
    return body, summary.judgments, identity
