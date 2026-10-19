"""Expose physical skill/prompt files that cannot satisfy principle inlining."""

from pathlib import Path

from .copilot_paths import copilot_prompt_path, copilot_skill_path
from .inventory import Asset, SKILL, MODE_PRINCIPLE
from .trees import GITHUB


def misplaced_reason(asset: Asset, tree: str, root: Path, reason: str | None) -> str | None:
    if asset.kind != SKILL or asset.mode != MODE_PRINCIPLE or tree != GITHUB:
        return reason
    paths = [path for path in (copilot_skill_path(asset.name, root),
                               copilot_prompt_path(asset.name, root)) if path.is_file()]
    if not paths:
        return reason
    detail = "misplaced files: " + ", ".join(path.relative_to(root).as_posix() for path in paths)
    return f"{reason}; {detail}" if reason else detail
