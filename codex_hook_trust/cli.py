"""Command-line interface for checking Codex hook trust."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

from .app_server import list_hooks
from .configuration import count_defined_handlers
from .repository import resolve_main_checkout

DEFAULT_TIMEOUT = 15.0


def build_parser():
    parser = argparse.ArgumentParser(prog="python3 -m codex_hook_trust")
    commands = parser.add_subparsers(dest="command", required=True)
    check = commands.add_parser("check", help="Codex フックの信頼状態を読む")
    check.add_argument("--repo", type=Path, default=Path.cwd())
    check.add_argument("--codex", default=os.environ.get("CODEX_HOOK_TRUST_CODEX", "codex"))
    check.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT)
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        if args.timeout <= 0 or args.timeout > DEFAULT_TIMEOUT:
            raise ValueError("--timeout must be greater than 0 and at most 15 seconds")
        repo = args.repo.resolve(strict=True)
        if not repo.is_dir():
            raise ValueError("--repo must be a directory")
        repo = resolve_main_checkout(repo)
        defined_count = count_defined_handlers(repo)
        hooks = list_hooks(args.codex, repo, args.timeout)
    except Exception as error:  # noqa: BLE001 - undetermined state maps to exit 2
        print(f"codex_hook_trust: 判定不能: {error}", file=sys.stderr)
        return 2

    project_hook_path = str((repo / ".codex" / "hooks.json").resolve())
    project_hooks = [hook for hook in hooks if hook.get("sourcePath") == project_hook_path]
    if len(project_hooks) < defined_count:
        project_section = json.dumps(str(repo), ensure_ascii=False)
        print(
            f"定義 {defined_count} 件に対し発見 {len(project_hooks)} 件。"
            "プロジェクト自体が Codex に信頼されていない可能性があります。"
        )
        print(
            f'確認先: ~/.codex/config.toml の [projects.{project_section}] '
            'trust_level = "trusted"'
        )
        print("復旧手順: .codex/hooks/README.md")
        return 1

    untrusted = [hook for hook in project_hooks if hook["trustStatus"] != "trusted"]
    if not untrusted:
        return 0
    print("未信頼の Codex フック:")
    for hook in untrusted:
        key = json.dumps(hook["key"], ensure_ascii=True)
        status = json.dumps(hook["trustStatus"], ensure_ascii=True)
        current_hash = json.dumps(hook["currentHash"], ensure_ascii=True)
        print(f"- {key} (trustStatus={status}, currentHash={current_hash})")
    return 1
