"""Assemble measurements, source coverage, and the current/previous comparison."""

import json
from datetime import datetime
from pathlib import Path

from . import activity, backlog, local, quality, read_github
from .comparison import compare
from .git_source import verify_repository
from .period import COLLECTION_START, NO_OBSERVED_TIME

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
    verify_repository(root, repository)
    reference = local.checkout(root, base_ref)
    github = read_github.collect(repository, period, max_pages)
    event_metrics, events, defect_inputs = activity.measure(period, repository, github["issues"], github["pulls"])
    stock_metrics, inventory = backlog.measure(observed_at, github)
    stock_metrics.update({
        "maintainability_violations": local.maintainability(root),
        "owner_pending_proposals": local.owner_proposals(root),
    })
    metrics = {**event_metrics, **quality.measure(period, github), **local.advisory(root, period)}
    if period.cutoff == period.start:
        metrics = {key: {**metric, "value": None, "reason": NO_OBSERVED_TIME} for key, metric in metrics.items()}
        events = dict.fromkeys(events)
    metrics = {**{key: {**value, "basis": "period"} for key, value in metrics.items()},
               **{key: {**value, "basis": "observation"} for key, value in stock_metrics.items()}}
    sources = {key: {field: value for field, value in github[key].items() if field != "rows"}
               for key in ("issues", "pulls", "ci")}
    data = {
        "schema_version": SCHEMA_VERSION, "repository": repository,
        "observed_at": observed_at.isoformat(), "observation_source": COLLECTION_START, "period": period.as_dict(),
        "reference": reference, "metrics": metrics, "sources": sources, "events": events,
        "inventory": inventory,
        "evidence": {"ci": github["ci"]["rows"], "reviews": github["reviews"], "defect_metrics": defect_inputs,
                     "pull_heads": quality.matching_heads(github)},
        "limitations": [
            "GitHub の状態・レビュー・依存は逐次取得した時点の観測です。過去時点の残数は復元しません。",
            activity.LATEST_CLOSE,
            "Issue/PR の移管・削除や取得中の更新は、API が公開する記録の範囲に限ります。",
        ],
    }
    data["comparison"] = compare(data, previous)
    return data
