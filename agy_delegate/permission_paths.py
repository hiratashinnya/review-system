"""許可rootと実行workspaceのcanonical包含境界を検査する。"""

from pathlib import Path

from .permission_rules import SAFE_PATH


def checked_directory(path: Path) -> Path:
    """存在する非link directoryだけを受け、別名や親への展開を許さない。"""
    if not isinstance(path, Path) or not path.is_absolute() or not SAFE_PATH.fullmatch(str(path)):
        raise ValueError("permission_path_invalid")
    try:
        if path != path.resolve(strict=True) or not path.is_dir():
            raise ValueError("permission_path_invalid")
        if any(part.is_symlink() for part in (path, *path.parents)):
            raise ValueError("permission_path_invalid")
    except (OSError, RuntimeError):
        raise ValueError("permission_path_invalid") from None
    return path


def effective_permission_root(workspace: Path, permission_root: Path | None = None) -> Path:
    """省略はworkspace。caller指定の親も内部proofによる起動照合を別途要する。"""
    workspace = checked_directory(workspace)
    root = checked_directory(workspace if permission_root is None else permission_root)
    if not workspace.is_relative_to(root):
        raise ValueError("permission_workspace_outside_root")
    return root


def corpus_roots(rules: object, root: Path) -> tuple[Path, ...]:
    """既知literalのroot/子corpus denyだけを受け、未知構文を安全扱いしない。"""
    if type(rules) is not list:
        raise ValueError("permission_corpus_rules_invalid")
    paths = []
    for rule in rules:
        if type(rule) is not str or not rule.startswith("write_file(") or not rule.endswith("/doc-system-v2/nodes)"):
            raise ValueError("permission_corpus_rules_invalid")
        value = rule[len("write_file("):-len("/doc-system-v2/nodes)")]
        path = Path(value)
        if str(path) != value or checked_directory(path) != path or not path.is_relative_to(root):
            raise ValueError("permission_corpus_rules_invalid")
        paths.append(path)
    if root not in paths or len(paths) != len(set(paths)):
        raise ValueError("permission_corpus_rules_invalid")
    return tuple(sorted(paths))
