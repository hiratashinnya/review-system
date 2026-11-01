"""未知層があっても既知群の危険を監査し、全層未完では不足を断定しない。"""

from pathlib import Path

from .permissions import expected_rules, inspect_permissions
from .settings_layer_types import SettingsResolution
from .settings_reads import read_layer_permissions

LAYER_NAMES = {"global", "project", "shared_user", "admin"}


def inspect_layer_resolution(resolution: SettingsResolution, workspace: Path, *,
                             expected: dict[str, list[str]] | None = None) -> list[str]:
    """保守的な危険rule監査であり、各engineのmerge規則は推定しない。"""
    reasons = list(resolution.reasons)
    names = [layer.name for layer in resolution.layers]
    complete = set(names) == LAYER_NAMES and len(names) == len(LAYER_NAMES)
    permissions = {group: [] for group in ("allow", "ask", "deny")}
    for layer in resolution.layers:
        if layer.name not in LAYER_NAMES:
            reasons.append("settings_layer_name_unknown")
            complete = False
            continue
        groups, known, problems = read_layer_permissions(layer)
        complete = complete and known
        reasons.extend(problems)
        for group, rules in groups.items():
            if len(rules) != len(set(rules)):
                reasons.append(f"settings_layer_duplicate_rules:{layer.name}:{group}")
            permissions[group].extend(rule for rule in rules if rule not in permissions[group])
    if not complete:
        reasons.append("settings_layer_inventory_incomplete")
    try:
        audit = inspect_permissions(permissions, expected_rules(workspace) if expected is None else expected)
        reasons.extend(reason for reason in audit if complete or not reason.startswith("missing_rules:"))
    except ValueError:
        reasons.append("unsafe_workspace_path")
    return list(dict.fromkeys(reasons))
