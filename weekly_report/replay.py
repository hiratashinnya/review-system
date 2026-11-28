"""Recalculate a bundle offline using its captured collection inputs."""

from datetime import datetime

from .period import Period, parse_jst

INPUT_VERSION = 1
EVENT_TIMES = {"closed_at", "created_at", "effective_at", "history_start", "merged_at", "submitted_at", "updated_at"}
ITEM_MAPS = {"blocked_by", "sub_issues", "reviews", "pull_files", "issue_events", "unavailable_issues"}


def previous_input(value):
    if value is None:
        return None
    fields = {"schema_version", "repository", "observed_at", "observation_source", "observation",
              "period", "metrics", "inventory"}
    return {key: item for key, item in value.items() if key in fields}


def restore_github(value, field=None):
    if isinstance(value, dict):
        return {int(key) if field in ITEM_MAPS else key: restore_github(item, key) for key, item in value.items()}
    if isinstance(value, list):
        return [restore_github(item) for item in value]
    if field in EVENT_TIMES and isinstance(value, str):
        moment = datetime.fromisoformat(value)
        if moment.tzinfo is None:
            raise ValueError("証跡の時刻に UTC オフセットがありません")
        return moment
    return value


def recalculate(value, previous=None):
    from .snapshot import SCHEMA_VERSION, assemble

    if value.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("snapshot の版に対応していません")
    payload = value.get("replay_inputs")
    if not isinstance(payload, dict) or payload.get("version") != INPUT_VERSION:
        raise ValueError("この snapshot には再集計用の取得証跡がありません。render で保存値を参照できます")
    fields = value["period"]
    period = Period(parse_jst(fields["start"]), parse_jst(fields["end"]), parse_jst(fields["observed_until"]))
    actual = parse_jst(payload["current_collection_at"])
    if period.cutoff > actual or period.as_dict() != fields:
        raise ValueError("snapshot の対象期間と観測上限が一致しません")
    raw_capture = payload["captured"]
    scope = raw_capture["collection_period"]
    if (not isinstance(scope, dict)
            or period.start < parse_jst(scope["start"]) or period.end > parse_jst(scope["end"])
            or period.cutoff != min(period.end, parse_jst(scope["observed_until"]))):
        raise ValueError("snapshot の対象期間が取得証跡の対象範囲と一致しません")
    capture = {**raw_capture, "github": restore_github(raw_capture["github"])}
    return assemble(value["repository"], period, capture, actual, payload["archive"],
                    previous_input(previous) if previous is not None else payload["previous"])
