"""実行結果へcwdと許可rootを別々に保存する。"""

from dataclasses import asdict

from .permission_paths import effective_permission_root
from .types import Request, Result


def execution_record(request: Request, result: Result) -> dict:
    """会話継続がrootを推定しないよう省略時もcanonical rootを明記する。"""
    root = effective_permission_root(request.workspace, request.permission_root)
    return asdict(result) | {"workspace": str(request.workspace), "permission_root": str(root)}
