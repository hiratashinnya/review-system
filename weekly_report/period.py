"""Resolve requested dates and limit event measurements to observed time."""

from dataclasses import dataclass
from datetime import datetime, time, timedelta, timezone

JST = timezone(timedelta(hours=9), "JST")
NO_OBSERVED_TIME = "観測済みの時間帯がありません"
COLLECTION_START = "collection_start"
WEEKDAYS = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")


def parse_jst(value):
    moment = datetime.fromisoformat(value)
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=JST)
    return moment.astimezone(JST)


@dataclass(frozen=True)
class Period:
    start: datetime
    end: datetime
    observed_at: datetime

    def __post_init__(self):
        if not self.start < self.end or self.observed_at < self.start:
            raise ValueError("開始 < 終了、かつ開始 <= 観測時点を指定してください")

    @property
    def cutoff(self):
        return min(self.end, self.observed_at)

    def contains(self, moment):
        return moment is not None and self.start <= moment < self.cutoff

    def as_dict(self):
        return {
            "start": self.start.isoformat(),
            "end": self.end.isoformat(),
            "observed_until": self.cutoff.isoformat(),
            "partial": self.cutoff < self.end,
            "boundary": "開始を含み、終了・観測上限を含まない (JST)",
        }


def resolve_cutoff(now, observed_at):
    cutoff = parse_jst(now) if now else observed_at or datetime.now(JST)
    return min(cutoff, observed_at) if observed_at is not None else cutoff


def week_beginning(day, week_start):
    offset = (day.weekday() - WEEKDAYS.index(week_start)) % len(WEEKDAYS)
    return datetime.combine(day - timedelta(days=offset), time.min, JST)


def resolve_period(start, end, now, *, observed_at=None, week_start="monday"):
    cutoff = resolve_cutoff(now, observed_at)
    if start is None and end is None:
        beginning = week_beginning(cutoff.date(), week_start)
        return Period(beginning, beginning + timedelta(days=7), cutoff)
    if start is None or end is None:
        raise ValueError("--start と --end は組で指定してください")
    return Period(parse_jst(start), parse_jst(end), cutoff)
