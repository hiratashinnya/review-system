"""Fake Codex app-server helpers shared by trust-check tests."""

import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
HOOK = ROOT / ".claude/hooks/codex-hook-trust-check.sh"
FAKE_SERVER = '''#!/usr/bin/env python3
import json, os, re, sys, time
mode = os.environ.get("FAKE_CODEX_MODE", "trusted")
trace_path = os.environ.get("FAKE_CODEX_TRACE")
def send(message):
    if mode == "standard":
        message = {"jsonrpc":"2.0", **message}
    print(json.dumps(message), flush=True)
def notify():
    send({"method":"server/notification", "params":{}})
def configured_hooks():
    path = os.path.abspath(os.path.join(os.getcwd(), ".codex", "hooks.json"))
    with open(path, encoding="utf-8") as stream:
        events = json.load(stream)["hooks"]
    hooks = []
    for event, groups in events.items():
        event_key = re.sub(r"(?<!^)(?=[A-Z])", "_", event).lower()
        for group_index, group in enumerate(groups):
            for handler_index, _ in enumerate(group["hooks"]):
                key = f"{path}:{event_key}:{group_index}:{handler_index}"
                hooks.append({"key":key, "trustStatus":"trusted",
                              "currentHash":"sha256:trusted"})
    return hooks
initialized = False
for line in sys.stdin:
    request = json.loads(line)
    if request.get("id") == 1:
        notify()
        send({"id":1, "result":{"userAgent":"codex/0.157.0", "codexHome":"/tmp/codex-home"}})
    elif request.get("method") == "initialized":
        initialized = True
    elif request.get("method") == "hooks/list":
        config_path = os.path.abspath(os.path.join(os.getcwd(), ".codex", "hooks.json"))
        if trace_path:
            record = {"cwd":os.getcwd(), "cwds":request.get("params", {}).get("cwds"),
                      "config_path":config_path}
            with open(trace_path, "a", encoding="utf-8") as stream:
                stream.write(json.dumps(record) + "\\n")
        if not initialized or request.get("params", {}).get("cwds") != [os.getcwd()]:
            send({"id":2, "error":{"message":"invalid request"}})
        elif mode == "malformed":
            print("not-json", flush=True)
            break
        elif mode == "timeout":
            time.sleep(10)
        elif mode == "server-request":
            send({"id":3, "method":"server/request", "params":{}})
        else:
            hooks = configured_hooks()
            if mode == "zero-hooks":
                hooks = []
            elif mode == "fewer-hooks":
                hooks = hooks[:-1]
            elif mode == "mixed":
                hooks[-1].update({"trustStatus":"untrusted", "currentHash":"sha256:current"})
            notify()
            send({"id":2, "result":{"data":[{"cwd":os.getcwd(), "hooks":hooks,
                                               "warnings":[], "errors":[]}]}})
'''


def make_fake_codex(directory):
    executable = Path(directory) / "codex-fake"
    executable.write_text(FAKE_SERVER, encoding="utf-8")
    executable.chmod(0o755)
    return executable


def _environment(executable, mode, extra_env=None):
    env = dict(os.environ)
    env.update(CODEX_HOOK_TRUST_CODEX=str(executable), FAKE_CODEX_MODE=mode)
    env.update(extra_env or {})
    return env


def run_check(executable, mode="trusted", *options, repo=ROOT, extra_env=None):
    return subprocess.run(
        [sys.executable, "-m", "codex_hook_trust", "check", "--repo", str(repo),
         *options], cwd=ROOT, capture_output=True, text=True, timeout=5,
        env=_environment(executable, mode, extra_env), check=False,
    )


def run_hook(executable, mode="trusted", *, repo=ROOT, extra_env=None):
    env = _environment(executable, mode, extra_env)
    env.update(CLAUDE_PROJECT_DIR=str(repo), PYTHONPATH=str(ROOT))
    return subprocess.run(
        ["bash", str(HOOK)], input='{"session_id":"payload-must-be-discarded"}',
        capture_output=True, text=True, timeout=25, env=env, check=False,
    )
