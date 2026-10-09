"""Fake Codex app-server executable used by trust-check tests."""

from pathlib import Path


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
                              "currentHash":"sha256:trusted", "sourcePath":path,
                              "source":"project"})
    return hooks
def user_hooks(count, trust_status="trusted"):
    path = os.path.abspath(os.path.join(
        os.environ.get("CODEX_HOME", "/tmp/codex-home"), "hooks.json",
    ))
    return [{"key":f"{path}:session_start:0:{index}",
             "trustStatus":trust_status, "currentHash":"sha256:user",
             "sourcePath":path, "source":"user"} for index in range(count)]
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
            elif mode == "project-one-short-user-one":
                hooks = hooks[:-1] + user_hooks(1)
            elif mode == "user-only-six":
                hooks = user_hooks(6)
            elif mode == "project-user-untrusted":
                hooks += user_hooks(1, "untrusted")
            elif mode == "mixed":
                hooks[-1].update({"trustStatus":"untrusted", "currentHash":"sha256:current"})
            notify()
            send({"id":2, "result":{"data":[{"cwd":os.getcwd(), "hooks":hooks,
                                               "warnings":[], "errors":[]}]}})
'''


def make_fake_codex(directory: str | Path) -> Path:
    """Write the fake app-server executable into a temporary directory."""
    executable = Path(directory) / "codex-fake"
    executable.write_text(FAKE_SERVER, encoding="utf-8")
    executable.chmod(0o755)
    return executable
