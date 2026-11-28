"""Compare matching metric definitions and adjacent observation windows."""

import math

from .capture_initiatives import compare_initiatives
from .capture_observations import compare as compare_observations
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
        if not isinstance(previous["metrics"], dict):
            raise ValueError("missing previous metrics")
        period_reason = None
        if old_end != start or end - start != old_end - old_start:
            period_reason = "対象期間が連続していないか、期間の長さが異なります"
        elif observed_span != old_observed_span:
            period_reason = "途中経過を含み、観測済みの期間の長さが異なります"
        elif not observed_span.total_seconds():
            period_reason = "観測済みの時間帯がありません"
        observation = compare_observations(current, previous, start + observed_span, old_start + old_observed_span)
        reasons = {"period": period_reason, "observation": observation["reason"]}
        metrics = _compare_metrics(current["metrics"], previous["metrics"], reasons)
        initiatives = compare_initiatives(current, previous, observation["reason"])
        return {**_status(period_reason), "metrics": metrics, "observation": observation,
                "initiative_changes": initiatives, **provenance}
    except (KeyError, ValueError, TypeError, AttributeError, OverflowError):
        return _unavailable("incomparable", "前回 snapshot の比較情報を解釈できません")


def _unavailable(status, reason):
    return {"status": status, "reason": reason, "metrics": {}}


def _numeric(value):
    return type(value) in (float, int) and math.isfinite(value)


def _status(reason):
    return {"status": "comparable" if reason is None else "incomparable", "reason": reason}


def _compare_metrics(current, previous, reasons):
    metrics = {}
    for key, item in current.items():
        old = previous.get(key)
        reason = reasons[item["basis"]]
        before = old.get("value") if isinstance(old, dict) else None
        if reason is None and (not isinstance(old, dict) or any(item.get(field) != old.get(field)
                                                               for field in ("basis", "definition", "unit"))):
            reason = "指標定義、算定単位または観測範囲が異なります"
        if reason is None and (not _numeric(before) or not _numeric(item["value"])):
            reason = "一方または両方が未計測です"
        metrics[key] = {"previous": before, "delta": None if reason else item["value"] - before,
                        "reason": reason}
    return metrics


def comparison_note(comparison, basis):
    if basis == "observation":
        actual = comparison.get("observation")
        if actual is None:
            return "取得時点の差は比較できません"
        reason = actual["reason"] or "取得時点どうしの比較"
        return f'{reason}　前回取得 {actual["previous_observed_at"]} ／ 今回取得 {actual["observed_at"]}'
    note = comparison["reason"] or "前回の対象期間と比較"
    if "previous_period" in comparison:
        previous = comparison["previous_period"]
        note += f'　前回対象 {previous["start"]} ～ {previous["end"]}'
    return note
