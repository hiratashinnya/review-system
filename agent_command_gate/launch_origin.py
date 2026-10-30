"""agy-delegate の起動元束縛: 実効 cwd を hook 配置位置由来の信頼ルートへ固定する（両 PF hook 共通）。

`python3 -m agy_delegate` は cwd 側の package を import する。呼出元 cwd が repo ルートである前提には
依存せず、宣言が無い場合は実プロセスの cwd を検査し、確定できなければ拒否する。
"""

import os
from typing import Callable

DENY_SUFFIX = "differs from the trusted agy_delegate launch root (the wrapper must run from the hook repository root)"


def launch_origin_reason(payload: dict, tool_input, trusted_root: str,
                         process_cwd: Callable[[], str] = os.getcwd) -> str | None:
    """拒否理由を返す。許可できる場合だけ None（宣言値は全て信頼ルートと一致し、基準 cwd も確定済み）。"""
    trusted = os.path.realpath(trusted_root)
    if not os.path.isfile(os.path.join(trusted, "agy_delegate", "__main__.py")):
        return "the trusted agy_delegate package was not found at the hook repository root"
    base, problem = _session_cwd(payload.get("cwd"), process_cwd)
    if problem:
        return f"{problem} and {DENY_SUFFIX}"
    declared = [("cwd" if payload.get("cwd") is not None else "process cwd", base)]
    if isinstance(tool_input, dict):
        declared += [(f"tool_input.{key}", tool_input.get(key)) for key in ("workdir", "cwd")]
    for source, value in declared:
        if value is None:
            continue
        if not isinstance(value, str) or not value:
            return f"{source} is not a usable directory path and {DENY_SUFFIX}"
        if os.path.realpath(os.path.join(base, value)) != trusted:
            return f"{source} {DENY_SUFFIX}"
    return None


def _session_cwd(declared, process_cwd: Callable[[], str]) -> tuple[str, str]:
    """(基準 cwd, 問題の説明)。payload.cwd が無ければ実プロセスの cwd を使い、確定できなければ問題を返す。"""
    if declared is None:
        try:
            return process_cwd(), ""
        except OSError:
            return "", "process cwd cannot be determined"
    if not isinstance(declared, str) or not os.path.isabs(declared):
        return "", "cwd is not an absolute directory path"
    return declared, ""
