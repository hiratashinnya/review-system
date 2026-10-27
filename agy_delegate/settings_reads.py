"""設定候補をリンク追跡せずbounded readし、部分監査と全層判定を区別する。"""

import os
import stat

from .settings_layer_types import PermissionGroups, SettingsLayer
from .strict_json import load_json

GROUPS = {"allow", "ask", "deny"}
MAX_BYTES = 1048576


def read_layer_permissions(layer: SettingsLayer) -> tuple[dict, bool, list[str]]:
    """理由は固定layer/group名のみ。未知schemaの内容やexception原文を返さない。"""
    name = layer.name
    if layer.path is None:
        return {}, False, [f"settings_layer_path_unidentified:{name}"]
    reading = False
    try:
        for path in (*reversed(layer.path.parents), layer.path):
            if stat.S_ISLNK(path.lstat().st_mode):
                return {}, False, [f"settings_layer_symlink_unsupported:{name}"]
        if layer.absent:
            return {}, False, [f"settings_layer_absence_mismatch:{name}"]
        if layer.decode_permissions is None:
            return {}, False, [f"settings_layer_schema_unverified:{name}"]
        if not hasattr(os, "O_NOFOLLOW") or not hasattr(os, "O_NONBLOCK"):
            return {}, False, [f"settings_layer_safe_open_unavailable:{name}"]
        reading = True
        descriptor = os.open(layer.path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(descriptor, "rb") as stream:
            before = os.fstat(stream.fileno())
            if not stat.S_ISREG(before.st_mode) or before.st_size > MAX_BYTES:
                raise ValueError("settings_not_bounded_regular")
            raw = stream.read(MAX_BYTES + 1)
            after = os.fstat(stream.fileno())
            attributes = ("st_dev", "st_ino", "st_mode", "st_size", "st_mtime_ns", "st_ctime_ns")
            if len(raw) > MAX_BYTES or any(getattr(before, key) != getattr(after, key) for key in attributes):
                raise ValueError("settings_read_changed")
        normalized = layer.decode_permissions(load_json(raw.decode("utf-8-sig")))
    except FileNotFoundError:
        return ({}, True, []) if layer.absent else ({}, False, [f"settings_layer_unreadable:{name}"])
    except OSError:
        reason = "settings_layer_unreadable_or_invalid" if reading else "settings_layer_unreadable"
        return {}, False, [f"{reason}:{name}"]
    except (UnicodeError, ValueError, TypeError, KeyError):
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
