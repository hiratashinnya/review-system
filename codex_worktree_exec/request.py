"""引数検査を通った起動要求（データだけを持つ）。"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ExecRequest:
    role: str
    worktree: Path
    prompt_file: Path
    output_file: Path
    model: str
    reasoning_effort: str
    timeout_seconds: int
