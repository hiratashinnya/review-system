"""公式根拠の限界を保持する runtime adapter。自己申告で解除しない。"""

from .settings_layer_types import SettingsResolution
from .settings_layers import inspect_layer_resolution
from .settings_sources import UNVERIFIED, resolve_candidate_sources
from .cohort_runtime import calibrated_runtime_reasons
from .native_policy import expected_file_only_rules
from .types import Request


def resolve_settings_layers(request: Request) -> SettingsResolution:
    """既知の層参加元だけ扱い、未特定の場所/形式/合成を推測しない。"""
    return resolve_candidate_sources(request.executable)


def verify_runtime(request: Request) -> list[str]:
    """全層監査と起動環境の根拠が揃わなければ子プロセス未起動で止める。"""
    resolution = resolve_settings_layers(request)
    try:
        expected = expected_file_only_rules(request.workspace)
    except (OSError, RuntimeError, ValueError):
        expected = None
    unsupported = [reason for reason in resolution.reasons if reason not in UNVERIFIED]
    if unsupported:
        return inspect_layer_resolution(resolution, request.workspace, expected=expected) + ["runtime_cohort_unverified"]
    reasons = calibrated_runtime_reasons(request, resolution)
    if reasons:
        return list(dict.fromkeys(inspect_layer_resolution(resolution, request.workspace, expected=expected) + reasons))
    return []
