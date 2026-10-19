"""ADR CLI の入力契約。"""
import argparse


def parser():
    result = argparse.ArgumentParser(description="道具別 harness ADR")
    commands = result.add_subparsers(dest="verb", required=True)
    for verb in ("new-entry", "check", "render", "todo", "stale", "file-issue",
                 "deps", "dependents", "orphans", "index"):
        command = commands.add_parser(verb)
        command.add_argument("--root", required=True)
        command.add_argument("--repo", default=".")
        if verb == "new-entry":
            command.add_argument("--draft", required=True)
        if verb == "stale":
            command.add_argument("--days", type=int, default=14)
        if verb in ("file-issue", "deps", "dependents"):
            command.add_argument("--id", required=True)
        if verb == "file-issue":
            command.add_argument("--create", action="store_true",
                                 help="省略時は下書き表示のみ")
            command.add_argument("--issue", type=int,
                                 help="作成済みIssue番号の復旧書戻し")
        if verb in ("check", "deps", "dependents", "orphans", "index"):
            command.add_argument("--envelope", action="append", default=[])
        if verb == "check":
            command.add_argument("--base", default="origin/main")
            command.add_argument("--require-base", action="store_true")
    return result
