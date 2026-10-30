"""論理templateを同じraw bytesから検査し、校正と通常実行へ束縛する。"""

import hashlib
from pathlib import Path

from .permission_paths import checked_directory, corpus_roots
from .permission_rules import expected_path_rules
from .permissions import inspect_permissions
from .settings_file_read import read_settings_bytes
from .strict_json import load_json


def read_logical_settings(settings: Path, root: Path) -> tuple[str, tuple[Path, ...]]:
    """bytesのhashと検査済corpus rootsを返す。native globalの代替ではない。"""
    try:
        raw = read_settings_bytes(settings)
        data = load_json(raw.decode("utf-8"))
    except (OSError, RuntimeError, ValueError, UnicodeError):
        raise ValueError("settings_unreadable_or_invalid") from None
    if type(data) is not dict or set(data) != {"permissions"}:
        raise ValueError("settings_extra_or_missing_keys")
    rules = data["permissions"]
    if type(rules) is not dict or set(rules) != {"allow", "ask", "deny"}:
        raise ValueError("permission_shape_invalid")
    roots = corpus_roots(rules["deny"], checked_directory(root))
    expected = expected_path_rules(str(root))
    expected["deny"] = [f"write_file({path}/doc-system-v2/nodes)" for path in roots]
    reasons = inspect_permissions(rules, expected)
    if reasons:
        raise ValueError(reasons[0])
    return hashlib.sha256(raw).hexdigest(), roots
