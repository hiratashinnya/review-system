"""論理templateより厳しい、実測済みfile-only native policy。"""

from pathlib import Path

from .native_paths import native_workspace_path
from .permission_rules import expected_path_rules
from .permission_paths import checked_directory


def expected_file_only_rules(workspace: Path, *, corpus_roots: tuple[Path, ...] = ()) -> dict[str, list[str]]:
    """一覧commandを許可済みと称さず、全command denyを明示する。"""
    root = checked_directory(workspace)
    roots = corpus_roots or (root,)
    if root not in roots or len(roots) != len(set(roots)):
        raise ValueError("permission_corpus_rules_invalid")
    for path in roots:
        if not checked_directory(path).is_relative_to(root):
            raise ValueError("permission_corpus_rules_invalid")
    logical = expected_path_rules(native_workspace_path(root))
    return {"allow": logical["allow"][:2], "ask": [],
            "deny": [*[f"write_file({native_workspace_path(path)}/doc-system-v2/nodes)" for path in roots],
                     "command(regex:.*)"]}
