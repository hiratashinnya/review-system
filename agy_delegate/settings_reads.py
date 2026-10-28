"""設定候補をリンク追跡せずbounded readし、部分監査と全層判定を区別する。"""

import os

from .settings_layer_types import PermissionGroups, SettingsLayer
from .settings_file_read import read_settings_bytes, validate_settings_path
from .strict_json import load_json

GROUPS = {"allow", "ask", "deny"}


def read_layer_permissions(layer: SettingsLayer) -> tuple[dict, bool, list[str]]:
    """理由は固定layer/group名のみ。未知schemaの内容やexception原文を返さない。"""
    name = layer.name
    if layer.path is None:
        return {}, False, [f"settings_layer_path_unidentified:{name}"]
    reading = False
    try:
        validate_settings_path(layer.path)
        if layer.absent:
            return {}, False, [f"settings_layer_absence_mismatch:{name}"]
        if layer.decode_permissions is None:
            return {}, False, [f"settings_layer_schema_unverified:{name}"]
        if not hasattr(os, "O_NOFOLLOW") or not hasattr(os, "O_NONBLOCK"):
            return {}, False, [f"settings_layer_safe_open_unavailable:{name}"]
        reading = True
        raw = read_settings_bytes(layer.path)
        normalized = layer.decode_permissions(load_json(raw.decode("utf-8-sig")))
    except FileNotFoundError:
        return ({}, True, []) if layer.absent else ({}, False, [f"settings_layer_unreadable:{name}"])
    except OSError:
        reason = "settings_layer_unreadable_or_invalid" if reading else "settings_layer_unreadable"
        return {}, False, [f"{reason}:{name}"]
    except ValueError as error:
        if str(error) == "settings_path_symlink":
            return {}, False, [f"settings_layer_symlink_unsupported:{name}"]
        return {}, False, [f"settings_layer_unreadable_or_invalid:{name}"]
    except (UnicodeError, TypeError, KeyError):
        return {}, False, [f"settings_layer_unreadable_or_invalid:{name}"]
    reasons, complete = [], True
    if isinstance(normalized, PermissionGroups):
        complete = not normalized.missing and not normalized.invalid
        reasons.extend(f"settings_layer_permission_group_unverified:{name}:{group}" for group in normalized.missing)
        reasons.extend(f"settings_layer_permission_type_invalid:{name}:{group}" for group in normalized.invalid)
        normalized = normalized.rules
    elif not isinstance(normalized, dict) or set(normalized) != GROUPS:
        return {}, False, [f"settings_layer_permission_shape_invalid:{name}"]
    rules = {}
    for group, values in normalized.items():
        if group not in GROUPS or not isinstance(values, list) or any(not isinstance(x, str) for x in values):
            reasons.append(f"settings_layer_permission_type_invalid:{name}")
            complete = False
        else:
            rules[group] = values
    return rules, complete, reasons
