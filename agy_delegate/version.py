"""出力契約の版を起動対象の実行ファイルへ束縛する。"""

import subprocess

from .output_contract import CONTRACT_VERSION
from .launch_profile import child_environment, native_arguments


def verified_version(request) -> str:
    child = subprocess.run(native_arguments(request.executable, "--version"),
                           cwd=request.workspace.resolve(), capture_output=True,
                           encoding="utf-8", errors="replace", timeout=10, check=False,
                           env=child_environment())
    if child.returncode or child.stderr.strip() or child.stdout.strip() != CONTRACT_VERSION:
        raise ValueError("agy_version_unverified_or_mismatch")
    return CONTRACT_VERSION
