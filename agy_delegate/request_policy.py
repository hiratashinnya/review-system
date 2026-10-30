"""Requestの論理許可snapshotとpath bindingを単一の検査経路で構築する。"""

from pathlib import Path

from .logical_settings import read_logical_settings
from .native_paths import native_workspace_path, text_sha256
from .permission_paths import effective_permission_root
from .types import Request


def policy_snapshot(request: Request) -> tuple[Path, str, tuple[Path, ...]]:
    """root/hash/deny rootsを返し、自己申告のproofやhashは受けない。"""
    root = effective_permission_root(request.workspace, request.permission_root)
    digest, roots = read_logical_settings(request.settings, root)
    if request.workspace not in roots:
        raise ValueError("permission_workspace_corpus_deny_missing")
    return root, digest, roots


def request_path_binding(request: Request) -> dict[str, str]:
    """native pathは入力射影であり、実cwd witnessとは区別する。"""
    root, digest, _ = policy_snapshot(request)
    return {"workspace_wsl_sha256": text_sha256(str(request.workspace)),
            "workspace_native_sha256": text_sha256(native_workspace_path(request.workspace)),
            "permission_root_wsl_sha256": text_sha256(str(root)),
            "permission_root_native_sha256": text_sha256(native_workspace_path(root)),
            "logical_settings_sha256": digest}
