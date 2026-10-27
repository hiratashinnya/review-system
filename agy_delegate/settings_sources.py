"""固定Windows exe配置から候補だけを導出する。適用/版/cwdの証明ではない。"""

import stat
from pathlib import Path

from .settings_decoders import decode_global_permissions
from .settings_layer_types import SettingsLayer, SettingsResolution

UNVERIFIED = (
    "settings_global_binding_unverified",
    "settings_project_binding_and_schema_unverified",
    "settings_shared_user_location_and_schema_unverified",
    "settings_admin_presence_or_precedence_unverified",
)


def resolve_candidate_sources(executable: Path) -> SettingsResolution:
    """aliasや未知配置は探索せず停止。cache・別UUID・Request.settingsへfallbackしない。"""
    try:
        if not executable.is_absolute() or ".." in executable.parts:
            raise ValueError("settings_executable_layout_unsupported")
        if executable.is_symlink():
            if executable != Path.home() / ".local/bin/agy":
                raise ValueError("settings_executable_symlink_unsupported")
            before = executable.lstat()
            canonical = executable.resolve(strict=True)
            after = executable.lstat()
            attributes = ("st_dev", "st_ino", "st_mode", "st_mtime_ns", "st_ctime_ns")
            if any(getattr(before, key) != getattr(after, key) for key in attributes):
                raise ValueError("settings_executable_alias_changed")
            executable = canonical
        for path in (executable, *executable.parents):
            if stat.S_ISLNK(path.lstat().st_mode):
                raise ValueError("settings_executable_symlink_unsupported")
        if not stat.S_ISREG(executable.lstat().st_mode):
            raise ValueError("settings_executable_not_regular")
        if tuple(executable.parts[-5:]) != ("AppData", "Local", "agy", "bin", "agy.exe"):
            raise ValueError("settings_executable_layout_unsupported")
        profile = executable.parents[4]
        if profile.parent.name != "Users":
            raise ValueError("settings_profile_layout_unsupported")
    except (OSError, ValueError) as error:
        reason = str(error) if isinstance(error, ValueError) else "settings_executable_unreadable"
        return SettingsResolution(reasons=(*UNVERIFIED, reason))
    root = profile / ".gemini"
    return SettingsResolution((
        SettingsLayer("global", root / "antigravity-cli/settings.json", decode_global_permissions),
        SettingsLayer("project", root / "config/projects/default-cli-project.json"),
        SettingsLayer("shared_user", root / "config/config.json"),
        SettingsLayer("admin", None),
    ), UNVERIFIED)
