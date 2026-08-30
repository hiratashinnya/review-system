"""Lightweight staleness signal between a parity seed and one of its mirrors.

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
_UNSET = object()


@dataclasses.dataclass(frozen=True, init=False)
class StaleSignal:
    parity_seed_epoch: int | None
    mirror_epoch: int | None
    day_gap: float | None
    parity_seed_lines: int
    mirror_lines: int
    size_ratio: float | None
    flagged: bool
    flag_reasons: tuple[str, ...]

    def __init__(
        self,
        parity_seed_epoch: int | None | object = _UNSET,
        mirror_epoch: int | None | object = _UNSET,
        day_gap: float | None | object = _UNSET,
        parity_seed_lines: int | object = _UNSET,
        mirror_lines: int | object = _UNSET,
        size_ratio: float | None | object = _UNSET,
        flagged: bool | object = _UNSET,
        flag_reasons: tuple[str, ...] | object = _UNSET,
        *,
        canonical_epoch: int | None | object = _UNSET,
        canonical_lines: int | object = _UNSET,
    ) -> None:
        """Accept v2 names and deprecated constructor keywords fail-closed."""
        resolved_epoch = _resolve_compat_value(
            "parity_seed_epoch", parity_seed_epoch, "canonical_epoch", canonical_epoch
        )
        resolved_lines = _resolve_compat_value(
            "parity_seed_lines", parity_seed_lines, "canonical_lines", canonical_lines
        )
        required = {
            "mirror_epoch": mirror_epoch,
            "day_gap": day_gap,
            "mirror_lines": mirror_lines,
            "size_ratio": size_ratio,
            "flagged": flagged,
            "flag_reasons": flag_reasons,
        }
        missing = [name for name, value in required.items() if value is _UNSET]
        if missing:
            raise TypeError(f"missing required argument(s): {', '.join(missing)}")
        object.__setattr__(self, "parity_seed_epoch", resolved_epoch)
        object.__setattr__(self, "mirror_epoch", mirror_epoch)
        object.__setattr__(self, "day_gap", day_gap)
        object.__setattr__(self, "parity_seed_lines", resolved_lines)
        object.__setattr__(self, "mirror_lines", mirror_lines)
        object.__setattr__(self, "size_ratio", size_ratio)
        object.__setattr__(self, "flagged", flagged)
        object.__setattr__(self, "flag_reasons", flag_reasons)

    @property
    def canonical_epoch(self) -> int | None:
        """Deprecated alias for ``parity_seed_epoch``."""
        return self.parity_seed_epoch

    @property
    def canonical_lines(self) -> int:
        """Deprecated alias for ``parity_seed_lines``."""
        return self.parity_seed_lines


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


def _resolve_compat_value(
    primary_name: str,
    primary_value: object,
    legacy_name: str,
    legacy_value: object,
) -> object:
    if primary_value is _UNSET and legacy_value is _UNSET:
        raise TypeError(f"missing required argument: {primary_name}")
    if (
        primary_value is not _UNSET
        and legacy_value is not _UNSET
        and primary_value != legacy_value
    ):
        raise TypeError(f"{primary_name} and {legacy_name} disagree")
    return legacy_value if primary_value is _UNSET else primary_value


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
