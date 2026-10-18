"""個別台帳文書の canonical 化、読取り、保存を行う。"""

from __future__ import annotations

from pathlib import Path

from . import paths as paths_module
from .model import (
    DocumentError,
    Finding,
    check_document_identity,
    normalize_document,
    parse_toml,
)
from .schema import DocSpec, filename_for
from .store import _relpath
from .tomlwrite import dumps


def canonical_text(spec: DocSpec, data: dict) -> str:
    return dumps(spec, data)


def load_draft(root, spec: DocSpec, draft) -> tuple[dict | None, list[Finding]]:
    """draft を読み、正規化データと検証 findings を返す。"""
    path = paths_module.draft_path(root, draft)
    relative = _relpath(Path(root), path)
    text = paths_module.read_text(path)
    raw = parse_toml(text)
    data, findings = normalize_document(spec, raw, relative)
    if data is not None:
        findings.extend(check_document_identity(spec, data, relative))
    return data, findings


def write_document(root, spec: DocSpec, data: dict) -> Path:
    """canonical 形式で保存し、読み戻しで元データと一致するか検証する。"""
    text = canonical_text(spec, data)
    target = paths_module.document_path(
        root, spec.subdir, filename_for(spec, data["id"]), create_dir=True
    )
    paths_module.write_text_atomic(target, text)

    reloaded = paths_module.read_text(target)
    if reloaded != text:
        raise DocumentError(f"書込み結果が canonical 表現と一致しない: {target}")
    roundtrip, findings = normalize_document(
        spec, parse_toml(reloaded), _relpath(Path(root), target)
    )
    if roundtrip is None or roundtrip != data:
        detail = "; ".join(finding.render() for finding in findings)
        raise DocumentError(
            f"ラウンドトリップ（書込み→読み戻し）で値が一致しない: {target} {detail}"
        )
    return target
