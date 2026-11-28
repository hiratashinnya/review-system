"""Issue #801: ownerが凍結したAC snapshotをレビュー期待値に束縛する。"""

from pathlib import Path

from . import ac_repository, paths
from .ac_snapshot import digest, from_issue_body
from .ac_snapshot_archive import path_for_stage, path_for_record
from .errors import KarteUsageError
from .review_expectation import allows_finding_only, require_snapshot_phase


def stage(repo_root, issue, round_no, source):
    """信頼済みcallerのIssue本文を保存し、roundとの照合期待値を発行。"""
    candidate = paths.resolve_within_repo(source, repo_root)
    body = paths.read_text(candidate)
    items = from_issue_body(body)
    archived = path_for_stage(repo_root, issue, round_no, body)
    if archived.exists():
        if paths.read_text(archived) != body:
            raise KarteUsageError("同一roundのAC snapshotの差し替えを拒否")
    else:
        paths.write_text_atomic(archived, body)
    identity = ac_repository.checkout_origin(repo_root)
    if identity is not None:
        ac_repository.bind(repo_root, archived, identity)
    record = {"digest": digest(items), "count": len(items),
              "source": str(archived.relative_to(Path(repo_root).resolve()))}
    if identity is not None:
        record.update(identity)
    return record


def read_for_dispatch(repo_root, issue, round_no):
    """進行ポインタに対応するtrusted AC snapshotを再検証して返す。"""
    from .active_pointer import read_active

    active = read_active(repo_root, required=True)
    if active.get("issue") != issue or active.get("round") != round_no - 1:
        raise KarteUsageError("review dispatchのAC snapshotと進行ポインタが不一致")
    if "review_expect" not in active:
        raise KarteUsageError("review envelopeの期待値が無い。主文脈の再activateが必要")
    if "ac_snapshot" not in active:
        if allows_finding_only(active["review_expect"], active.get("legacy_finding_only")):
            return None
        raise KarteUsageError("AC snapshot無しのreview envelopeは受理しない")
    require_snapshot_phase(active["review_expect"])
    record = active["ac_snapshot"]
    if not isinstance(record, dict) or set(record) not in (
            {"digest", "count", "source"}, {"digest", "count", "source", "host", "repository"}):
        raise KarteUsageError("AC snapshotの期待値が不正")
    path = path_for_record(repo_root, issue, round_no, record)
    frozen = ac_repository.frozen(repo_root, path)
    if frozen != ({key: record[key] for key in ("host", "repository")}
                  if "host" in record else None):
        raise KarteUsageError("review dispatchのorigin束縛が不一致")
    criteria = from_issue_body(paths.read_text(path))
    if (type(record["count"]) is not int or record["count"] != len(criteria)
            or record["digest"] != digest(criteria)):
        raise KarteUsageError("AC snapshotの原本と期待値が不一致")
    return record, criteria


def validate(repo_root, issue, round_no, report):
    """レビューア本文のACはmainが凍結した原本と一致する場合に限り受理。"""
    from .active_pointer import read_active
    from .review_summary import parse_summary

    active = read_active(repo_root, required=True)
    require_snapshot_phase(active.get("review_expect"))
    record = active.get("ac_snapshot")
    if not isinstance(record, dict) or set(record) not in (
            {"digest", "count", "source"}, {"digest", "count", "source", "host", "repository"}):
        raise KarteUsageError("mainによるAC snapshotの期待値が無い")
    file = path_for_record(repo_root, issue, round_no, record)
    frozen = ac_repository.frozen(repo_root, file)
    if frozen != ({key: record[key] for key in ("host", "repository")}
                  if "host" in record else None):
        raise KarteUsageError("review取り込みのorigin束縛が不一致")
    items = from_issue_body(paths.read_text(file))
    if record["digest"] != digest(items) or type(record["count"]) is not int or record["count"] != len(items):
        raise KarteUsageError("AC snapshotの原本と期待値が不一致")
    summary = parse_summary(report, issue)
    if summary is None:
        raise KarteUsageError("reviewerのReportにはReview Summaryが必須")
    if summary.ac_snapshot_digest != record["digest"] or summary.ac_count != record["count"]:
        raise KarteUsageError("レビューAC判定が凍結済みIssue ACと一致しない")
    return summary
