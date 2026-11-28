"""Run single-period and batched collection through the same evidence pipeline."""

import argparse

from . import capture_observations, output, snapshot
from .batch_periods import pending_slot, period_for_slot, resolve_slots
from .capture import acquire
from .git_source import verify_repository
from .github import normalize_repository
from .period import Period, WEEKDAYS


def positive_int(raw):
    value = int(raw)
    if value < 1:
        raise argparse.ArgumentTypeError("1 以上を指定してください")
    return value


def add_options(collect):
    collect.add_argument("--week-start", default="monday", choices=WEEKDAYS, type=str.lower,
                         help="週の開始曜日（既定 monday）")
    collect.add_argument("--week", help="この日付を含む週（YYYY-MM-DD）")
    collect.add_argument("--weeks", type=positive_int,
                         help="--week から先の週数。--week 省略時は当週までの過去週数")
    collect.add_argument("--month", help="暦月を週単位に分割して一括生成（YYYY-MM）")
    collect.add_argument("--observations", action="append", metavar="SNAPSHOT",
                         help="対象期間に実測した保存 snapshot。複数指定可")


def collect(args, root, observed_at, previous):
    repository = normalize_repository(args.repository)
    slots, cutoff = resolve_slots(args, observed_at)
    archives = capture_observations.load(args.observations, repository, snapshot.SCHEMA_VERSION)
    periods = [period_for_slot(start, end, cutoff) for start, end in slots]
    available = [period for period in periods if period is not None]
    captured = None
    if available:
        envelope = Period(available[0].start, available[-1].end, cutoff)
        captured = acquire(root, repository, args.base_ref, envelope, args.max_pages)
    else:
        verify_repository(root, repository)
    results = []
    for period, (start, end) in zip(periods, slots, strict=True):
        if period is None:
            results.append(pending_slot(repository, start, end))
        else:
            assert captured is not None
            archive = capture_observations.select(period, observed_at, archives)
            data = snapshot.assemble(repository, period, captured, observed_at, archive, previous)
            results.append(data)
            previous = data
    if len(results) == 1 and available and args.month is None:
        return output.write(results[0], None, args.out, root)
    return output.write_batch(results, args.out, root)
