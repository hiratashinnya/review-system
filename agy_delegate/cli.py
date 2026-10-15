"""read-only 許可診断と、検査省略のない直接実行入口。"""

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from .permissions import inspect_settings
from .runner import run, run_parallel
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
            command.add_argument("--prompt", required=True, action="append")
            command.add_argument("--max-concurrency", type=int)
            command.add_argument("--print-timeout", type=int, required=True)
            command.add_argument("--conversation")
            command.add_argument("--images", action="store_true")
            command.add_argument("--brain", type=Path)
            command.add_argument("--caller-state", choices=("ready", "stopped"), required=True)
    args = vars(parser.parse_args(argv))
    command = args.pop("command")
    if command == "inspect":
        reasons = inspect_settings(args["settings"], args["workspace"])
        print(json.dumps({"classification": "static_valid" if not reasons else "invalid",
                          "reasons": reasons, "effective_settings_verified": False}, ensure_ascii=False))
        return int(bool(reasons))
    prompts = args.pop("prompt")
    concurrency = args.pop("max_concurrency")
    if len(prompts) > 1 and (concurrency is None or args["conversation"]):
        parser.error("multiple prompts require --max-concurrency and no --conversation")
    if concurrency is not None and not 1 <= concurrency <= 8:
        parser.error("--max-concurrency must be 1..8")
    requests = [Request(**args, prompt=prompt) for prompt in prompts]
    results = run_parallel(requests, max_concurrency=concurrency) if len(prompts) > 1 else [run(requests[0])]
    for result in results:
        _print_result(result)
    return int(any(result.exit_code for result in results))


def _print_result(result):
    public = asdict(result)
    public["response"] = "[redacted: local result.json]" if result.response is not None else None
    public["error"] = "[redacted: local result.json]" if result.error is not None else None
    public["denied_actions"] = ["[redacted]" for action in result.denied_actions]
    public["artifacts"] = ["[local artifact]" for artifact in result.artifacts]
    print(json.dumps(public, ensure_ascii=False))
