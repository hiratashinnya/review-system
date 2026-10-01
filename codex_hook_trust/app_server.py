"""Read Codex hook registrations from the local app-server."""

from __future__ import annotations

import subprocess
import time
from pathlib import Path

from .jsonrpc import read_result, send_message, start_reader


def _stop_process(process):
    try:
        process.stdin.close()
    except OSError:
        pass
    try:
        process.terminate()
    except ProcessLookupError:
        pass
    try:
        process.wait(timeout=1)
    except subprocess.TimeoutExpired:
        try:
            process.kill()
        except ProcessLookupError:
            pass
        process.wait(timeout=1)


def _validate_hooks(result):
    data = result.get("data")
    if not isinstance(data, list) or not data or not isinstance(data[0], dict):
        raise ValueError("hooks/list result has no data entry")
    hooks = data[0].get("hooks")
    if not isinstance(hooks, list):
        raise ValueError("hooks/list result has no hooks list")
    for hook in hooks:
        if not isinstance(hook, dict) or any(
            not isinstance(hook.get(field), str) or not hook[field]
            for field in ("key", "trustStatus", "currentHash")
        ):
            raise ValueError("hooks/list returned an invalid hook entry")
    return hooks


def list_hooks(codex, repo: Path, timeout: float):
    """Run initialize/initialized/hooks-list and return validated entries."""
    process = subprocess.Popen(
        [codex, "app-server", "--stdio"], cwd=repo, stdin=subprocess.PIPE,
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True,
    )
    assert process.stdin is not None and process.stdout is not None
    try:
        messages = start_reader(process.stdout)
        deadline = time.monotonic() + timeout
        send_message(process.stdin, {
            "jsonrpc": "2.0", "id": 1, "method": "initialize",
            "params": {"clientInfo": {"name": "codex-hook-trust", "version": "1.0.0"}},
        })
        read_result(messages, 1, deadline)
        send_message(process.stdin, {"jsonrpc": "2.0", "method": "initialized", "params": {}})
        send_message(process.stdin, {
            "jsonrpc": "2.0", "id": 2, "method": "hooks/list",
            "params": {"cwds": [str(repo)]},
        })
        return _validate_hooks(read_result(messages, 2, deadline))
    finally:
        _stop_process(process)
