"""A documented non-mirror: one asset that is intentionally absent from one tree."""

from __future__ import annotations

import dataclasses


@dataclasses.dataclass(frozen=True)
class Exemption:
    name: str
    kind: str
    tree: str
    reason: str
