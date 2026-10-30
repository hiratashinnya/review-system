"""公式global schemaの明示ruleを射影する。engine全体の実効既定値ではない。"""

import re

from .settings_layer_types import PermissionGroups

GROUPS = ("allow", "ask", "deny")
RULE = re.compile(r"(command|read_file|write_file|read_url|execute_url|mcp|unsandboxed)\(.*\)")


def decode_global_permissions(data: object) -> PermissionGroups:
    """optional群は明示rule無しとして記録し、不正群は停止へ渡す。"""
    if not isinstance(data, dict):
        raise ValueError("global_object_required")
    permissions = data.get("permissions", {})
    if not isinstance(permissions, dict):
        raise ValueError("global_permissions_object_required")
    if set(permissions) - set(GROUPS):
        raise ValueError("global_permissions_unknown_members")
    rules, omitted, invalid = {}, [], []
    for group in GROUPS:
        if group not in permissions:
            rules[group] = []
            omitted.append(group)
        elif not isinstance(permissions[group], list) or any(
                not isinstance(value, str) or not RULE.fullmatch(value) for value in permissions[group]):
            invalid.append(group)
        else:
            rules[group] = list(permissions[group])
    return PermissionGroups(rules, invalid=tuple(invalid), omitted=tuple(omitted))
