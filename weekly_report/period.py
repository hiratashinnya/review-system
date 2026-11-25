"""Resolve requested dates and limit event measurements to observed time."""

from dataclasses import dataclass
from datetime import datetime, time, timedelta, timezone

JST = timezone(timedelta(hours=9), "JST")


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


def resolve_period(start, end, now):
    observed_at = parse_jst(now) if now else datetime.now(JST)
    if start is None and end is None:
        today = observed_at.date()
        monday = today - timedelta(days=today.weekday())
        beginning = datetime.combine(monday, time.min, JST)
        return Period(beginning, beginning + timedelta(days=7), observed_at)
    if start is None or end is None:
        raise ValueError("--start と --end は組で指定してください")
    return Period(parse_jst(start), parse_jst(end), observed_at)
