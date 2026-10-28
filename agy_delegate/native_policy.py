"""論理templateより厳しい、実測済みfile-only native policy。"""

from pathlib import Path

from .native_paths import native_workspace_path
from .permission_rules import expected_path_rules


def expected_file_only_rules(workspace: Path) -> dict[str, list[str]]:
    """一覧commandを許可済みと称さず、全command denyを明示する。"""
    logical = expected_path_rules(native_workspace_path(workspace))
    return {"allow": logical["allow"][:2], "ask": [],
            "deny": [*logical["deny"], "command(regex:.*)"]}
