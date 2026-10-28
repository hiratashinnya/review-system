"""校正済opaque空snapshotとglobal明示profileを、OS子起動前に監査する。"""

import hashlib
from pathlib import Path

from .native_policy import expected_file_only_rules
from .permissions import inspect_permissions
from .settings_file_read import read_settings_bytes
from .settings_layer_types import SettingsResolution
from .settings_reads import read_layer_permissions


def offline_snapshot_reasons(resolution: SettingsResolution, proof: dict, workspace: Path) -> list[str]:
    """project/shared一般schemaを推測せず、校正した全bytesの不変だけを認定する。"""
    layers = {layer.name: layer for layer in resolution.layers}
    if set(layers) != {"global", "project", "shared_user", "admin"} or len(resolution.layers) != 4:
        return ["cohort_source_inventory_unverified"]
    try:
        expected = expected_file_only_rules(workspace)
    except (OSError, RuntimeError, ValueError):
        return ["cohort_native_projection_unsupported"]
    rules, known, reasons = read_layer_permissions(layers["global"])
    if known:
        reasons.extend(inspect_permissions(rules, expected))
    for label, name in (("global", "global"), ("project", "project"), ("shared", "shared_user")):
        path = layers[name].path
        if path is None:
            reasons.append("cohort_source_path_unverified")
            continue
        try:
            raw = read_settings_bytes(path)
            exists, digest = True, hashlib.sha256(raw).hexdigest()
        except FileNotFoundError:
            exists, digest = False, None
        except (OSError, ValueError):
            reasons.append("cohort_local_snapshot_unreadable")
            continue
        baseline = proof["files"][label]
        if exists != baseline["exists"] or digest != baseline["sha256"]:
            reasons.append("cohort_local_snapshot_mismatch")
    return list(dict.fromkeys(reasons))
