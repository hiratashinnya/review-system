"""#575 の設定形式を read-only 検査する。設定層合成の保証とは区別する。"""

import re
from pathlib import Path

from .strict_json import load_json

SAFE_PATH = re.compile(r"[A-Za-z0-9 /_.:\-\u3040-\u309f\u30a0-\u30ff\u3400-\u4dbf\u4e00-\u9fff]+\Z")


def expected_rules(workspace: Path) -> dict[str, list[str]]:
    """レビュー対象の限定テンプレート。path 以外の可変正規表現は認めない。"""
    path = str(workspace.resolve())
    if not SAFE_PATH.fullmatch(path):
        raise ValueError("unsafe_workspace_path")
    command = "Get-ChildItem -Name '" + path + "'"
    pattern = "^" + re.escape(command) + "$(?![\\s\\S])"
    return {
        "allow": [f"read_file({path})", f"write_file({path})", f"command(regex:{pattern})"],
        "ask": [],
        "deny": [f"write_file({path}/doc-system-v2/nodes)"],
    }


def inspect_settings(settings: Path, workspace: Path) -> list[str]:
    """未検査キー/競合/過剰許可も停止する。ファイルを変更しない。"""
    try:
        data = load_json(settings.read_text(encoding="utf-8"))
        expected = expected_rules(workspace)
    except (OSError, ValueError, UnicodeError):
        return ["settings_unreadable_or_invalid"]
    if not isinstance(data, dict) or set(data) != {"permissions"}:
        return ["settings_extra_or_missing_keys"]
    return inspect_permissions(data["permissions"], expected)


def inspect_permissions(permissions: object, expected: dict[str, list[str]]) -> list[str]:
    """正規化済み許可の限定契約検査。適用層・合成の証明は担当しない。"""
    if not isinstance(permissions, dict) or set(permissions) != set(expected):
        return ["permission_shape_invalid"]
    reasons = []
    for group, required in expected.items():
        actual = permissions[group]
        if not isinstance(actual, list) or any(not isinstance(x, str) for x in actual):
            reasons.append(f"permission_type_invalid:{group}")
            continue
        if len(actual) != len(set(actual)):
            reasons.append(f"duplicate_rules:{group}")
        if set(required) - set(actual):
            reasons.append(f"missing_rules:{group}")
        if set(actual) - set(required):
            reasons.append(f"unreviewed_or_conflicting_rules:{group}")
    return reasons
