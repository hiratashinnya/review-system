"""出力契約の版を起動対象の実行ファイルへ束縛する。"""

import subprocess

from .output_contract import CONTRACT_VERSION


def verified_version(request) -> str:
    child = subprocess.run([str(request.executable.resolve()), "--version"],
                           cwd=request.workspace.resolve(), capture_output=True,
                           encoding="utf-8", errors="replace", timeout=10, check=False)
    if child.returncode or child.stderr.strip() or child.stdout.strip() != CONTRACT_VERSION:
        raise ValueError("agy_version_unverified_or_mismatch")
    return CONTRACT_VERSION
