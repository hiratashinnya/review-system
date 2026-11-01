"""実測対象のproject選択と子process限定auto-update抑止を組み立てる。"""

import os
from pathlib import Path

PROJECT_SELECTOR = "default-cli-project"
UPDATE_VARIABLE = "AGY_CLI_DISABLE_AUTO_UPDATE"


def native_arguments(executable: Path, *arguments: str) -> list[str]:
    """通常APIへ任意selector注入の入口を増やさず、全native起動で共通化する。"""
    return [str(executable.resolve()), "--project", PROJECT_SELECTOR, *arguments]


def child_environment() -> dict[str, str]:
    """既存process/global設定を保存せず、WSL→Win32子への継承だけを限定する。"""
    environment = os.environ.copy()
    entries = [entry for entry in environment.get("WSLENV", "").split(":")
               if entry and entry.split("/")[0].casefold() != UPDATE_VARIABLE.casefold()]
    environment[UPDATE_VARIABLE] = "true"
    environment["WSLENV"] = ":".join([*entries, UPDATE_VARIABLE + "/w"])
    return environment
