"""read-only 許可診断と、検査省略のない直接実行入口。"""

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from .permissions import inspect_settings
from .runner import run
from .types import Request


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="agy 契約検査（実機 adapter 未確認時は停止）")
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("inspect", "run"):
        command = commands.add_parser(name)
        command.add_argument("--workspace", type=Path, required=True)
        command.add_argument("--settings", type=Path, required=True)
        if name == "run":
            command.add_argument("--executable", type=Path, required=True)
            command.add_argument("--prompt", required=True)
            command.add_argument("--print-timeout", type=int, required=True)
            command.add_argument("--conversation")
            command.add_argument("--writes", action="store_true")
            command.add_argument("--images", action="store_true")
            command.add_argument("--brain", type=Path)
            command.add_argument("--caller-stopped", action="store_true")
    args = vars(parser.parse_args(argv))
    command = args.pop("command")
    if command == "inspect":
        reasons = inspect_settings(args["settings"], args["workspace"])
        print(json.dumps({"classification": "static_valid" if not reasons else "invalid",
                          "reasons": reasons, "effective_settings_verified": False}, ensure_ascii=False))
        return int(bool(reasons))
    result = run(Request(**args))
    public = asdict(result)
    public["response"] = "[redacted: local result.json]" if result.response is not None else None
    public["error"] = "[redacted: local result.json]" if result.error is not None else None
    public["denied_actions"] = ["[redacted]" for action in result.denied_actions]
    public["artifacts"] = ["[local artifact]" for artifact in result.artifacts]
    print(json.dumps(public, ensure_ascii=False))
    return result.exit_code
