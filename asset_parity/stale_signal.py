"""Staleness signal value and legacy field compatibility."""

from __future__ import annotations

import dataclasses

from .compat_value import _UNSET, _resolve_compat_value


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


