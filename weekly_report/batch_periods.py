"""Resolve contiguous week slots, preserving calendar and observation boundaries."""

from datetime import date, timedelta

from .period import Period, parse_jst, resolve_cutoff, resolve_period, week_beginning

WEEK = timedelta(days=7)


def _month_slots(month, week_start):
    if len(month) != 7:
        raise ValueError("--month は YYYY-MM 形式で指定してください")
    start = parse_jst(date.fromisoformat(month + "-01").isoformat())
    end = parse_jst(((start.date() + timedelta(days=31)).replace(day=1)).isoformat())
    week = week_beginning(start.date(), week_start)
    while week < end:
        yield max(start, week), min(end, week + WEEK)
        week += WEEK


def _week_slots(anchor, count, week_start, cutoff):
    day = date.fromisoformat(anchor) if anchor else cutoff.date()
    start = week_beginning(day, week_start)
    if anchor is None:
        start -= WEEK * (count - 1)
    for index in range(count):
        beginning = start + WEEK * index
        yield beginning, beginning + WEEK


def resolve_slots(args, observed_at):
    explicit = args.start is not None or args.end is not None
    if explicit and (args.week or args.weeks is not None or args.month):
        raise ValueError("--start/--end と --week/--weeks/--month は併用できません")
    if args.month and (args.week or args.weeks is not None):
        raise ValueError("--month と --week/--weeks は併用できません")
    cutoff = resolve_cutoff(args.now, observed_at)
    if args.month:
        slots = list(_month_slots(args.month, args.week_start))
    elif args.week or args.weeks is not None:
        slots = list(_week_slots(args.week, args.weeks or 1, args.week_start, cutoff))
    else:
        period = resolve_period(args.start, args.end, args.now, observed_at=observed_at,
                                week_start=args.week_start)
        return [(period.start, period.end)], cutoff
    return slots, cutoff


def period_for_slot(start, end, cutoff):
    if cutoff < start:
        return None
    return Period(start, end, cutoff)


def pending_slot(repository, start, end):
    return {
        "repository": repository, "status": "not_arrived", "reason": "対象期間にまだ到達していません",
        "period": {"start": start.isoformat(), "end": end.isoformat(), "observed_until": None, "partial": True},
    }
