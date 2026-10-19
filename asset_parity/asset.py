"""Asset identity and deprecated constructor compatibility."""

from __future__ import annotations

import dataclasses
from pathlib import Path

_UNSET = object()


@dataclasses.dataclass(frozen=True, init=False)
class Asset:
    name: str
    kind: str  # SKILL | AGENT
    mode: str | None
    parity_seed_path: Path

    def __init__(
        self,
        name: str,
        kind: str,
        mode: str | None,
        parity_seed_path: Path | object = _UNSET,
        *,
        canonical_path: Path | object = _UNSET,
    ) -> None:
        """Accept the v2 name and the deprecated constructor keyword.

        Supplying both names is allowed only when their values agree.
        """
        if parity_seed_path is _UNSET and canonical_path is _UNSET:
            raise TypeError("missing required argument: parity_seed_path")
        if (
            parity_seed_path is not _UNSET
            and canonical_path is not _UNSET
            and parity_seed_path != canonical_path
        ):
            raise TypeError("parity_seed_path and canonical_path disagree")
        resolved_path = canonical_path if parity_seed_path is _UNSET else parity_seed_path
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "kind", kind)
        object.__setattr__(self, "mode", mode)
        object.__setattr__(self, "parity_seed_path", resolved_path)

    @property
    def canonical_path(self) -> Path:
        """Deprecated alias for ``parity_seed_path``; retained for compatibility."""
        return self.parity_seed_path


