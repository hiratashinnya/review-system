"""Compare matching metric definitions and adjacent observation windows."""

import math

from .period import parse_jst


def _span(period):
    start, end = parse_jst(period["start"]), parse_jst(period["end"])
    cutoff = parse_jst(period["observed_until"])
    if not start <= cutoff <= end or start >= end or period["partial"] != (cutoff < end):
        raise ValueError("invalid comparison period")
    return start, end, cutoff - start


def compare(current, previous):
    if previous is None:
        return _unavailable("initial", "比較用の前回 snapshot が指定されていません")
    try:
        if (previous["schema_version"] != current["schema_version"]
                or previous["repository"] != current["repository"]):
            return _unavailable("incomparable", "対象リポジトリまたは snapshot の版が異なります")
        start, end, observed_span = _span(current["period"])
        old_start, old_end, old_observed_span = _span(previous["period"])
        provenance = {"previous_period": previous["period"],
                      "previous_observed_at": previous["observed_at"]}
        if old_end != start or end - start != old_end - old_start:
            return _unavailable("incomparable", "対象期間が連続していないか、期間の長さが異なります") | provenance
        if observed_span != old_observed_span:
            return _unavailable("incomparable", "途中経過を含み、観測済みの期間の長さが異なります") | provenance
        if not isinstance(previous["metrics"], dict):
            raise ValueError("missing previous metrics")
        metrics = _compare_metrics(current["metrics"], previous["metrics"])
        return {"status": "comparable", "reason": None, "metrics": metrics, **provenance}
    except (KeyError, ValueError, TypeError, AttributeError, OverflowError):
        return _unavailable("incomparable", "前回 snapshot の比較情報を解釈できません")


def _unavailable(status, reason):
    return {"status": status, "reason": reason, "metrics": {}}


def _numeric(value):
    return type(value) in (float, int) and math.isfinite(value)


def _compare_metrics(current, previous):
    metrics = {}
    for key, item in current.items():
        old = previous.get(key)
        reason = None
        before = old.get("value") if isinstance(old, dict) else None
        if item["basis"] != "period":
            reason = "残数・検査は観測時点の値です"
        elif not isinstance(old, dict) or any(item[field] != old.get(field)
                                              for field in ("basis", "definition", "unit")):
            reason = "指標定義、算定単位または観測範囲が異なります"
        elif not _numeric(before) or not _numeric(item["value"]):
            reason = "一方または両方が未計測です"
        metrics[key] = {"previous": before, "delta": None if reason else item["value"] - before,
                        "reason": reason}
    return metrics
