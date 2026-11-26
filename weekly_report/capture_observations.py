"""Select and preserve observations made during the requested reporting period."""

from hashlib import sha256
import json
from pathlib import Path

from .capture_stock import archive_inputs
from .period import COLLECTION_START, parse_jst

SEQUENTIAL_LIMIT = "逐次収集の開始時刻です。期間末の状態を同時に取得した証跡がありません"


def load(paths, repository, schema_version):
    results = []
    for path in paths or []:
        source = Path(path).read_bytes()
        value = json.loads(source)
        if (value["repository"] != repository or value["schema_version"] != schema_version
                or value.get("observation_source") != COLLECTION_START):
            raise ValueError(f"観測 snapshot のリポジトリ・版・観測根拠が一致しません ({path})")
        results.append((value, sha256(source).hexdigest()))
    return results


def select(period, actual, archives):
    if actual == period.cutoff:
        return None
    candidates = []
    for value, digest in archives:
        instant = parse_jst(value["observed_at"])
        past = value["period"]
        if (parse_jst(past["start"]) == period.start and parse_jst(past["end"]) == period.end
                and period.start <= instant <= period.cutoff):
            observation = value.get("observation") or {}
            reference = observation.get("reference", value["reference"])
            evidence = value["evidence"].get("saved_observation", value["evidence"])
            captured = archive_inputs(value, instant)
            stock = {"capture": captured} if captured is not None else _preserved_observation(value)
            candidates.append((instant, digest, {
                "observed_at": instant.isoformat(), "sha256": digest, "reference": reference, **stock,
                "evidence": {key: evidence.get(key) for key in
                             ("ci", "reviews", "pull_heads", "head_ci", "pull_files", "consistency")},
            }))
    if not candidates:
        return None
    latest, _, selected = max(candidates, key=lambda row: row[:2])
    for instant, digest, value in candidates:
        if instant == latest and value != (selected | {"sha256": digest}):
            raise ValueError("同一取得時刻の保存 snapshot に異なる観測結果があります")
    return selected


def _preserved_observation(value):
    return {"metrics": {key: metric for key, metric in value["metrics"].items() if metric["basis"] == "observation"},
            "inventory": value["inventory"]}


def describe(period, actual, archive):
    observed = parse_jst(archive["observed_at"]) if archive else actual
    if archive:
        kind = "saved"
    elif actual >= period.end or actual > period.cutoff:
        kind = "retrospective"
    else:
        kind = "current"
    if observed == period.end:
        reason = SEQUENTIAL_LIMIT
    elif observed <= period.cutoff:
        reason = "対象期間末とは異なる時点の実測です"
    else:
        reason = "後日の取得です。対象期間末の状態を裏付ける実測 snapshot がありません"
    result = {"kind": kind, "observed_at": observed.isoformat(), "current_collection_at": actual.isoformat(),
              "period_end_status": "not_measured", "period_end_reason": reason}
    if archive:
        result["source_snapshot_sha256"] = archive["sha256"]
    return result


def _valid_as_of(data, instant, cutoff):
    if instant >= cutoff:
        return True
    source = data.get("observation") or {}
    return (source.get("kind") == "saved" and bool(source.get("source_snapshot_sha256"))
            and parse_jst(data["period"]["start"]) <= instant)


def compare(current, previous, cutoff, previous_cutoff):
    now, before = parse_jst(current["observed_at"]), parse_jst(previous["observed_at"])
    reason = None
    if any(data.get("observation_source") != COLLECTION_START for data in (current, previous)):
        reason = "実際の取得開始時刻と確認できない snapshot があります"
    elif not _valid_as_of(current, now, cutoff) or not _valid_as_of(previous, before, previous_cutoff):
        reason = "取得時点が、記録された期間イベントの観測上限より前にあります"
    elif before >= now:
        reason = "前回の取得時点が今回より前にありません"
    return {"status": "comparable" if reason is None else "incomparable", "reason": reason,
            "previous_observed_at": before.isoformat(), "observed_at": now.isoformat()}
