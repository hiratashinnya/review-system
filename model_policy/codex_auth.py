"""同一 Codex context の認証方式だけを識別し、資格情報は出力しない。"""

import subprocess


def codex_auth_mode(runner=subprocess.run):
    try:
        completed = runner(["codex", "login", "status"], capture_output=True,
                           text=True, check=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        raise ValueError("STOP: Codex 認証方式を確認できません") from None
    status = (completed.stdout or "") + "\n" + (completed.stderr or "")
    backend = "Logged in using ChatGPT" in status
    api = any(marker in status for marker in ("Logged in using an API key", "Logged in using API key"))
    if backend and not api:
        return "backend"
    if api and not backend:
        return "api"
    raise ValueError("STOP: Codex 認証方式が不明です")
