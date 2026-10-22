"""全層の read-only 検査と保守的な許可監査。実効 merge の推定はしない。"""

from pathlib import Path

from .permissions import expected_rules, inspect_permissions
from .settings_layer_types import SettingsResolution
from .strict_json import load_json

LAYER_NAMES = {"global", "project", "shared_user", "admin"}


def inspect_layer_resolution(resolution: SettingsResolution, workspace: Path) -> list[str]:
    """未知/未読の層を飛ばさず停止。成功でも保守的監査で実効合成未証明。"""
    reasons = list(resolution.reasons)
    names = [layer.name for layer in resolution.layers]
    if set(names) != LAYER_NAMES or len(names) != len(LAYER_NAMES):
        reasons.append("settings_layer_inventory_incomplete")
    permissions = {group: [] for group in ("allow", "ask", "deny")}
    for layer in resolution.layers:
        if layer.name not in LAYER_NAMES or layer.path is None:
            reasons.append(f"settings_layer_path_unidentified:{layer.name}")
            continue
        try:
            layer.path.lstat()
        except FileNotFoundError:
            if not layer.absent:
                reasons.append(f"settings_layer_unreadable:{layer.name}")
            continue
        except OSError:
            reasons.append(f"settings_layer_unreadable:{layer.name}")
            continue
        if layer.absent:
            reasons.append(f"settings_layer_absence_mismatch:{layer.name}")
            continue
        if layer.decode_permissions is None:
            reasons.append(f"settings_layer_schema_unverified:{layer.name}")
            continue
        try:
            normalized = layer.decode_permissions(load_json(layer.path.read_text(encoding="utf-8")))
        except (OSError, UnicodeError, ValueError, TypeError, KeyError):
            reasons.append(f"settings_layer_unreadable_or_invalid:{layer.name}")
            continue
        if not isinstance(normalized, dict) or set(normalized) != set(permissions):
            reasons.append(f"settings_layer_permission_shape_invalid:{layer.name}")
            continue
        for group, rules in normalized.items():
            if not isinstance(rules, list) or any(not isinstance(rule, str) for rule in rules):
                reasons.append(f"settings_layer_permission_type_invalid:{layer.name}:{group}")
                continue
            if len(rules) != len(set(rules)):
                reasons.append(f"settings_layer_duplicate_rules:{layer.name}:{group}")
            permissions[group].extend(rule for rule in rules if rule not in permissions[group])
    if reasons:
        return list(dict.fromkeys(reasons))
    try:
        reasons.extend(inspect_permissions(permissions, expected_rules(workspace)))
    except ValueError:
        reasons.append("unsafe_workspace_path")
    return list(dict.fromkeys(reasons))
