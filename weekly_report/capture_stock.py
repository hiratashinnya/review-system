"""Measure state at acquisition, including reusable archived evidence."""

from . import backlog, ledger
from .period import parse_jst
from .replay import INPUT_VERSION, restore_github


def measure(github, ledger_evidence, instant):
    metrics, inventory = backlog.measure(instant, github)
    metrics.update(ledger.observation_metrics(ledger_evidence, observed_at=instant))
    return metrics, inventory


def archive_inputs(snapshot, instant):
    evidence = snapshot.get("replay_inputs") or {}
    if evidence.get("version") != INPUT_VERSION:
        return None
    archive = evidence["archive"]
    if archive is not None:
        if parse_jst(archive["observed_at"]) != instant:
            raise ValueError("保存 snapshot の観測時刻と元の証跡が一致しません")
        return archive.get("capture")
    if parse_jst(evidence["current_collection_at"]) != instant:
        raise ValueError("保存 snapshot の観測時刻と取得証跡が一致しません")
    capture = evidence["captured"]
    return {"github": {key: capture["github"][key] for key in ("issues", "pulls", "blocked_by", "sub_issues")},
            "ledger": {key: capture["ledger"][key] for key in ("maintainability", "owner_proposals", "karte")}}


def from_archive(archive):
    captured = archive.get("capture")
    if captured is None:
        return archive["metrics"], archive["inventory"]
    return measure(restore_github(captured["github"]), captured["ledger"], parse_jst(archive["observed_at"]))
