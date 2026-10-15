"""停止状態の Copilot template からローカル runtime agent を生成する。"""

import re

from .policy import ROOT


def invalidate_agents(root=ROOT):
    for path in (root / ".github/agents").glob("runtime-*.agent.md"):
        body = path.read_text(encoding="utf-8")
        body = body.replace("disable-model-invocation: false", "disable-model-invocation: true")
        body = body.replace("user-invocable: true", "user-invocable: false")
        body = re.sub(r"^このファイルは解決済み runtime です。.*$",
                      "この runtime は停止済みです。モデル準備手順を再実行するまで起動しないでください。",
                      body, flags=re.M)
        path.write_text(body, encoding="utf-8")


def prepare_agents(policy, resolved, root=ROOT):
    outputs = {}
    prepared = {}
    for name, tier in policy["copilot_agents"].items():
        source = root / f".github/agents/{name}.agent.md"
        body = source.read_text(encoding="utf-8")
        body = re.sub(r"^name:.*$", f"name: runtime-{name}", body, count=1, flags=re.M)
        body = body.replace("disable-model-invocation: true", "disable-model-invocation: false")
        body = body.replace("user-invocable: false", "user-invocable: true")
        body = body.replace("---\n", f"---\nmodel: {resolved[tier]}\n", 1)
        body = re.sub(r"^このファイルは停止状態の template です。.*$",
                      f"このファイルは解決済み runtime です。実使用モデルが {resolved[tier]} と一致することを確認し、共通本文を遂行してください。",
                      body, flags=re.M)
        target = source.with_name(f"runtime-{name}.agent.md")
        prepared[target] = body
        outputs[name] = {"agent": f"runtime-{name}", "model": resolved[tier]}
    for target, body in prepared.items():
        target.write_text(body, encoding="utf-8")
    return outputs
