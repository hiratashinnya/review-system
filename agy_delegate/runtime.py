"""公式根拠の限界を保持する runtime adapter。自己申告で解除しない。"""

from .settings_layer_types import SettingsResolution
from .settings_layers import inspect_layer_resolution
from .settings_sources import resolve_candidate_sources
from .types import Request


def resolve_settings_layers(request: Request) -> SettingsResolution:
    """既知の層参加元だけ扱い、未特定の場所/形式/合成を推測しない。"""
    return resolve_candidate_sources(request.executable)


def verify_runtime(request: Request) -> list[str]:
    """全層監査と起動環境の根拠が揃わなければ子プロセス未起動で止める。"""
    return inspect_layer_resolution(resolve_settings_layers(request), request.workspace) + [
        "settings_permission_merge_unverified", "launch_environment_unverified",
        "print_timeout_format_unverified"]
