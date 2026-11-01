"""proof schema の固定型・日時・hash 検査。"""

import re
from datetime import datetime, timedelta, timezone


def exact_object(value: object, fields: set[str]) -> dict:
    if type(value) is not dict or set(value) != fields:
        raise ValueError("cohort_schema_invalid")
    return value


def checked_hash(value: object) -> str:
    if type(value) is not str or not re.fullmatch(r"[0-9a-f]{64}", value):
        raise ValueError("cohort_hash_invalid")
    return value


def checked_protocol(value: object) -> None:
    if type(value) is not int or value != 1:
        raise ValueError("cohort_protocol_invalid")


def checked_lifetime(created: object, expires: object, now: datetime) -> None:
    if not isinstance(now, datetime) or now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("cohort_clock_invalid")
    start, end = _utc_time(created), _utc_time(expires)
    if not start < end or end - start > timedelta(hours=24):
        raise ValueError("cohort_lifetime_invalid")
    if not start <= now.astimezone(timezone.utc) < end:
        raise ValueError("cohort_expired_or_future")


def _utc_time(value: object) -> datetime:
    if type(value) is not str or not re.fullmatch(
        r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|\+00:00)", value
    ):
        raise ValueError("cohort_time_invalid")
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise ValueError("cohort_time_invalid") from None
