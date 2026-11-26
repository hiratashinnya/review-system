"""Assemble measurements, source coverage, and the current/previous comparison."""

import json
from datetime import datetime
from pathlib import Path

from . import activity, capture_stock, history, ledger, quality
from .capture import acquire
from .capture_observations import describe
from .comparison import compare
from .period import COLLECTION_START, NO_OBSERVED_TIME
from .replay import INPUT_VERSION, previous_input

SCHEMA_VERSION = 1


def _serialize(value):
    if isinstance(value, datetime):
        return value.isoformat()
    raise TypeError(f"unexpected JSON value: {type(value).__name__}")


def dumps(value):
    return json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False, default=_serialize) + "\n"


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def collect(root, repository, base_ref, period, max_pages, previous, *, observed_at):
    captured = acquire(root, repository, base_ref, period, max_pages)
    return assemble(repository, period, captured, observed_at, None, previous)


def assemble(repository, period, captured, observed_at, archive, previous):
    github, reference = captured["github"], captured["reference"]
    event_metrics, events, defect_inputs = activity.measure(period, repository, github["issues"], github["pulls"],
                                                            transitions=github.get("transitions"))
    observation = describe(period, observed_at, archive)
    if archive:
        stock_metrics, inventory = capture_stock.from_archive(archive)
        observation["reference"] = archive["reference"]
    else:
        stock_metrics, inventory = capture_stock.measure(github, captured["ledger"], observed_at)
    metrics = event_metrics | quality.measure(period, github) | ledger.period_metrics(period, captured["ledger"])
    if period.cutoff == period.start:
        metrics = {key: {**metric, "value": None, "status": "not_measured", "reason": NO_OBSERVED_TIME}
                   for key, metric in metrics.items()}
        events = dict.fromkeys(events)
    metrics.update(history.measure(captured["main_history"], period.cutoff))
    metrics = {**{key: {**value, "basis": "period"} for key, value in metrics.items()},
               **{key: {**value, "basis": "observation"} for key, value in stock_metrics.items()}}
    sources = {key: {field: value for field, value in github[key].items() if field != "rows"}
               for key in ("issues", "pulls", "ci")}
    ci = github["ci"]["rows"]
    evidence = {"ci": None if ci is None else [row for row in ci if period.contains(row["created_at"])],
                "reviews": github["reviews"], "defect_metrics": defect_inputs,
                "pull_heads": quality.matching_heads(github), "transitions": github.get("transitions"),
                "head_ci": github.get("head_ci"), "pull_files": github.get("pull_files"),
                "consistency": github.get("consistency")}
    if archive:
        evidence["saved_observation"] = archive["evidence"]
    data = {
        "schema_version": SCHEMA_VERSION, "repository": repository,
        "observed_at": observation["observed_at"], "observation_source": COLLECTION_START,
        "observation": observation, "period": period.as_dict(), "collection_period": captured["collection_period"],
        "reference": reference, "metrics": metrics, "sources": sources, "events": events,
        "inventory": inventory, "evidence": evidence,
        "replay_inputs": {"version": INPUT_VERSION, "captured": captured, "archive": archive,
                          "previous": previous_input(previous), "current_collection_at": observed_at.isoformat()},
        "limitations": [
            "GitHub の状態・レビュー・依存は逐次取得した時点の観測です。後日取得と対象期間内の実測を区別します。",
            activity.LATEST_CLOSE,
            "Issue/PR の移管・削除や取得中の更新は、API が公開する記録の範囲に限ります。",
        ],
    }
    data["comparison"] = compare(data, previous)
    return data
