"""正本パスと生成対象の選択を定義する。"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Mapping

from ai_layout import NON_ACTIVE_SHARED_DIRS

REPO_ROOT = Path(__file__).resolve().parents[1]
COMMON_SOURCE = ".ai/guidance/common.md"
PRINCIPLES_SOURCE = ".ai/skills/spec-principles/SKILL.md"
TARGETS: Mapping[str, str] = {
    "AGENTS.md": ".ai/guidance/platforms/codex.md",
    ".github/copilot-instructions.md": ".ai/guidance/platforms/copilot.md",
}
NON_GUIDANCE_SHARED_DIRS: tuple[str, ...] = tuple(
    f"{directory}/" for directory in NON_ACTIVE_SHARED_DIRS
)
PRINCIPLES_MARKER_RE = re.compile(
    rb"<!--\s*principles-source:\s*\.ai/skills/spec-principles/SKILL\.md;\s*"
    rb"sha256:\s*([0-9a-f]{64})\s*-->"
)
