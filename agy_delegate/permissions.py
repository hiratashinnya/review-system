"""#575 の設定形式を read-only 検査する。設定層合成の保証とは区別する。"""

from pathlib import Path

from .permission_rules import expected_path_rules


def expected_rules(workspace: Path) -> dict[str, list[str]]:
    """レビュー対象の限定テンプレート。path 以外の可変正規表現は認めない。"""
    return expected_path_rules(str(workspace.resolve()))


def inspect_settings(settings: Path, workspace: Path) -> list[str]:
    """未検査キー/競合/過剰許可も停止する。ファイルを変更しない。"""
    from .logical_settings import read_logical_settings
    try:
        read_logical_settings(settings, workspace)
    except ValueError as error:
        return [str(error)]
    return []


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
