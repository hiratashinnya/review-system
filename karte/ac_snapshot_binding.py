"""Issue #801: ownerが凍結したAC snapshotをレビュー期待値に束縛する。"""

from pathlib import Path

from . import paths
from .ac_snapshot import digest, from_issue_body
from .errors import KarteUsageError


def _archived(repo_root, issue, number):
    directory = paths.karte_dir(repo_root, create=True)
    return paths.resolve_within_repo(directory / f"issue-{issue}-ac-round-{number}.md", repo_root)


def stage(repo_root, issue, round_no, source):
    """信頼済みcallerのIssue本文を保存し、roundとの照合期待値を発行。"""
    candidate = paths.resolve_within_repo(source, repo_root)
    body = paths.read_text(candidate)
    items = from_issue_body(body)
    archived = _archived(repo_root, issue, round_no)
    if archived.exists():
        if paths.read_text(archived) != body:
            raise KarteUsageError("同一roundのAC snapshotの差し替えを拒否")
    else:
        paths.write_text_atomic(archived, body)
    return {"digest": digest(items), "count": len(items),
            "source": str(archived.relative_to(Path(repo_root).resolve()))}


def read_for_dispatch(repo_root, issue, round_no):
    """進行ポインタに対応するtrusted AC snapshotを再検証して返す。"""
    from .active_pointer import read_active

    active = read_active(repo_root, required=True)
    if active.get("issue") != issue or active.get("round") != round_no - 1:
        raise KarteUsageError("review dispatchのAC snapshotと進行ポインタが不一致")
    record = active.get("ac_snapshot")
    if record is None:
        if active.get("legacy_finding_only") is True:
            return None  # 明示した既存findingのみの互換経路。AC判定を保証しない。
        raise KarteUsageError("AC snapshot無しのreview envelopeは受理しない")
    if not isinstance(record, dict) or set(record) != {"digest", "count", "source"}:
        raise KarteUsageError("AC snapshotの期待値が不正")
    path = _archived(repo_root, issue, round_no)
    if record["source"] != str(path.relative_to(Path(repo_root).resolve())):
        raise KarteUsageError("AC snapshotの保存先が不一致")
    criteria = from_issue_body(paths.read_text(path))
    if (type(record["count"]) is not int or record["count"] != len(criteria)
            or record["digest"] != digest(criteria)):
        raise KarteUsageError("AC snapshotの原本と期待値が不一致")
    return record, criteria


def validate(repo_root, issue, round_no, report):
    """レビューア本文のACはmainが凍結した原本と一致する場合に限り受理。"""
    from .active_pointer import read_active
    from .review_summary import parse_summary

    record = read_active(repo_root, required=True).get("ac_snapshot")
    if not isinstance(record, dict) or set(record) != {"digest", "count", "source"}:
        raise KarteUsageError("mainによるAC snapshotの期待値が無い")
    file = _archived(repo_root, issue, round_no)
    if record["source"] != str(file.relative_to(Path(repo_root).resolve())):
        raise KarteUsageError("AC snapshotの保存先が不一致")
    items = from_issue_body(paths.read_text(file))
    if record["digest"] != digest(items) or type(record["count"]) is not int or record["count"] != len(items):
        raise KarteUsageError("AC snapshotの原本と期待値が不一致")
    summary = parse_summary(report, issue)
    if summary is None:
        raise KarteUsageError("reviewerのReportにはReview Summaryが必須")
    if summary.ac_snapshot_digest != record["digest"] or summary.ac_count != record["count"]:
        raise KarteUsageError("レビューAC判定が凍結済みIssue ACと一致しない")
    return summary
