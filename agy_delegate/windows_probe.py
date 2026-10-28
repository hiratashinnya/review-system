"""固定sourceの読取専用Windows workerを起動する内部OS境界。agyは起動しない。"""

import json
import subprocess
import uuid
from pathlib import Path

from .launch_profile import child_environment
from .native_paths import native_executable_path, native_workspace_path
from .strict_json import load_json
from .types import Request
from .windows_binding_values import validated_windows_reply

POWERSHELL = "/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe"


def read_windows_binding(request: Request) -> dict:
    """request pathをshell codeへ挿入せず、bounded nonce frameをstdinへ渡す。"""
    try:
        worker = Path(__file__).with_name("windows_binding.ps1")
        nonce = uuid.uuid4().hex
        payload = {"nonce": nonce,
                   "native_executable": native_executable_path(request.executable.resolve(strict=True)),
                   "native_workspace": native_workspace_path(request.workspace)}
        child = subprocess.run([POWERSHELL, "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
                                "-File", native_workspace_path(worker)],
                               input=json.dumps(payload) + "\n", cwd=request.workspace.resolve(strict=True),
                               capture_output=True, encoding="utf-8-sig", errors="strict", timeout=20,
                               check=False, env=child_environment())
        if child.returncode or child.stderr.strip() or len(child.stdout) > 65536:
            raise ValueError("cohort_windows_binding_unverified")
        return validated_windows_reply(load_json(child.stdout), nonce)
    except (OSError, RuntimeError, ValueError, subprocess.TimeoutExpired):
        raise ValueError("cohort_windows_binding_unverified") from None
