"""Lightweight staleness signal between a canonical asset and one of its mirrors.

This is explicitly **not** a semantic diff — the issue #155 audit that motivated this
tool found that cross-format content comparison (e.g. Claude Code SKILL.md prose vs. a
Codex TOML `developer_instructions` string) needs an LLM or a human, not deterministic
tooling. This module only computes a rough, cheap signal and FLAGS pairs that are
"worth a look" — false positives are acceptable (the caller decides what to do with a
flag; this never blocks anything on its own).

Two signals, either of which can flag a pair:
  * last-commit-date gap (via `git log -1 --format=%ct -- <path>`, in days)
  * line-count ratio (crude proxy for size drift across differing file formats)

The git-log call is injected (`commit_epoch_fn`) so tests don't need a real git
history — this follows this repo's test-strategy convention of isolating the
non-deterministic/external boundary (here: subprocess+git) behind a swappable seam.
"""

from __future__ import annotations

import dataclasses
import subprocess
from pathlib import Path
from typing import Callable

DEFAULT_DAY_THRESHOLD = 30
DEFAULT_SIZE_RATIO_THRESHOLD = 2.0  # flag if one side has >2x the lines of the other

CommitEpochFn = Callable[[Path, Path], "int | None"]


@dataclasses.dataclass(frozen=True)
class StaleSignal:
    canonical_epoch: int | None
    mirror_epoch: int | None
    day_gap: float | None
    canonical_lines: int
    mirror_lines: int
    size_ratio: float | None
    flagged: bool
    flag_reasons: tuple[str, ...]


def git_last_commit_epoch(path: Path, root: Path) -> int | None:
    """Unix-epoch seconds of the last commit touching `path`, or None (fail-soft).

    None covers: not a git repo, file untracked/never committed, or git unavailable —
    this is an informational signal, never a hard error.
    """
    try:
        rel = path.relative_to(root)
    except ValueError:
        rel = path
    try:
        proc = subprocess.run(
            ["git", "log", "-1", "--format=%ct", "--", str(rel)],
            cwd=root, capture_output=True, text=True, timeout=10, check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    out = (proc.stdout or "").strip()
    return int(out) if out.isdigit() else None


def _line_count(path: Path) -> int:
    try:
        return len(path.read_text(encoding="utf-8").splitlines())
    except OSError:
        return 0


def compare(
    canonical_path: Path,
    mirror_path: Path,
    root: Path,
    *,
    day_threshold: int = DEFAULT_DAY_THRESHOLD,
    size_ratio_threshold: float = DEFAULT_SIZE_RATIO_THRESHOLD,
    commit_epoch_fn: CommitEpochFn = git_last_commit_epoch,
) -> StaleSignal:
    c_epoch = commit_epoch_fn(canonical_path, root)
    m_epoch = commit_epoch_fn(mirror_path, root)
    reasons: list[str] = []

    day_gap = None
    if c_epoch is not None and m_epoch is not None:
        day_gap = abs(c_epoch - m_epoch) / 86400.0
        if day_gap > day_threshold:
            reasons.append(f"last-commit gap {day_gap:.0f}d > {day_threshold}d threshold")

    c_lines = _line_count(canonical_path)
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
        canonical_epoch=c_epoch,
        mirror_epoch=m_epoch,
        day_gap=day_gap,
        canonical_lines=c_lines,
        mirror_lines=m_lines,
        size_ratio=size_ratio,
        flagged=bool(reasons),
        flag_reasons=tuple(reasons),
    )
