"""Lightweight date and size staleness heuristics; never a semantic diff."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from .commit_epoch import git_last_commit_epoch
from .compat_value import _UNSET, _resolve_compat_value
from .stale_signal import StaleSignal

DEFAULT_DAY_THRESHOLD = 30
DEFAULT_SIZE_RATIO_THRESHOLD = 2.0
CommitEpochFn = Callable[[Path, Path], "int | None"]


def _line_count(path: Path) -> int:
    try:
        return len(path.read_text(encoding="utf-8").splitlines())
    except OSError:
        return 0


def compare(
    parity_seed_path: Path | object = _UNSET,
    mirror_path: Path | object = _UNSET,
    root: Path | object = _UNSET,
    *,
    canonical_path: Path | object = _UNSET,
    day_threshold: int = DEFAULT_DAY_THRESHOLD,
    size_ratio_threshold: float = DEFAULT_SIZE_RATIO_THRESHOLD,
    commit_epoch_fn: CommitEpochFn = git_last_commit_epoch,
) -> StaleSignal:
    parity_seed_path = _resolve_compat_value(
        "parity_seed_path", parity_seed_path, "canonical_path", canonical_path
    )
    if mirror_path is _UNSET:
        raise TypeError("missing required argument: mirror_path")
    if root is _UNSET:
        raise TypeError("missing required argument: root")
    c_epoch = commit_epoch_fn(parity_seed_path, root)
    m_epoch = commit_epoch_fn(mirror_path, root)
    reasons: list[str] = []

    day_gap = None
    if c_epoch is not None and m_epoch is not None:
        day_gap = abs(c_epoch - m_epoch) / 86400.0
        if day_gap > day_threshold:
            reasons.append(f"last-commit gap {day_gap:.0f}d > {day_threshold}d threshold")

    c_lines = _line_count(parity_seed_path)
    m_lines = _line_count(mirror_path)
    size_ratio = None
    if c_lines and m_lines:
        size_ratio = max(c_lines, m_lines) / min(c_lines, m_lines)
        if size_ratio > size_ratio_threshold:
            reasons.append(
                f"size ratio {size_ratio:.1f}x > {size_ratio_threshold}x threshold "
                f"({c_lines} vs {m_lines} lines)"
            )
    elif c_lines == 0 or m_lines == 0:
        reasons.append("empty file on one side")

    return StaleSignal(
        parity_seed_epoch=c_epoch,
        mirror_epoch=m_epoch,
        day_gap=day_gap,
        parity_seed_lines=c_lines,
        mirror_lines=m_lines,
        size_ratio=size_ratio,
        flagged=bool(reasons),
        flag_reasons=tuple(reasons),
    )
