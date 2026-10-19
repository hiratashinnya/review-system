"""`.ai/guidance/` から PF 常駐入口を生成し、drift を検査する。

Claude は公式 ``@`` import で共通原稿を直接読むため、この生成対象には含めない。
`.ai/rationale/`、`.ai/troubleshooting/`、`.ai/schema/` は非活性の共有記録／契約で
あり、常駐 guidance の入力にも生成物にも含めない。
pre-commit 向け検査は working tree を参照せず staged index だけを読み、自動生成も
自動 stage も行わない。
"""

from __future__ import annotations

import argparse
from typing import Iterable, Sequence

from .filesystem import check, render
from .staged import staged_check


def _print_errors(errors: Iterable[str]) -> None:
    for error in errors:
        print(f"guidance-sync: ERROR: {error}")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("render", "check", "staged-check"))
    args = parser.parse_args(argv)
    if args.command == "render":
        changed = render()
        if changed:
            for target in changed:
                print(f"guidance-sync: rendered {target}")
        else:
            print("guidance-sync: generated files are already current")
        return 0
    errors = check() if args.command == "check" else staged_check()
    if errors:
        _print_errors(errors)
        return 1
    print(f"guidance-sync: {args.command} OK")
    return 0
