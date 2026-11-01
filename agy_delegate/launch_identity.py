"""実行前に許可したleaf shimだけを一度解決し、同canonical pathを後段へ渡す。"""

from dataclasses import replace
from pathlib import Path

from .types import Request


def canonical_launch_request(request: Request) -> Request:
    """runtime検査後に別aliasへ再解決してしまう起動を防ぐ。"""
    executable = request.executable
    for part in (executable, *executable.parents):
        if part.is_symlink() and (part != executable or part != Path.home() / ".local/bin/agy"):
            raise ValueError("executable_alias_unsupported")
    try:
        canonical = executable.resolve(strict=True)
    except (OSError, RuntimeError):
        raise ValueError("executable_identity_unverified") from None
    return replace(request, executable=canonical)
