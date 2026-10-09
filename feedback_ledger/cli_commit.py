"""Validation and atomic persistence shared by writing commands."""

from __future__ import annotations

from pathlib import Path

from . import paths as paths_module
from .check import check_canonical, check_id_references, check_paths_exist, check_proposals, check_triage
from .cli_support import EXIT_OK, _errors, _fail
from .model import Finding
from .store import Document, canonical_text, load_draft, load_store, write_document

def _preflight(root, spec, data, *, base_locus: str | None = None) -> list[Finding]:
    """書込み前に、確定後の姿でしか判定できない規則（L2/L3/P2〜P4/T1/L7）を先に掛ける。

    既存の別文書に起因する findings は**混ぜない**（locus 前方一致で絞る）。壊れた既存文書が
    あることを理由に新しいオーナー判断の記録を拒むと、価値経路を遮断する（PR6）。
    """
    store = load_store(root)
    relpath = f"{paths_module.FEEDBACK_DIRNAME}/{spec.subdir}/{data['id']}.toml"
    document = Document(
        kind=spec.kind,
        document_id=data["id"],
        relpath=relpath,
        path=Path(root) / relpath,
        data=data,
        text=canonical_text(spec, data),
    )
    others = [item for item in store.of(spec.kind) if item.document_id != data["id"]]
    store.documents[spec.kind] = sorted(others + [document], key=lambda item: item.relpath)
    findings = (
        check_paths_exist(store)
        + check_id_references(store)
        + check_proposals(store, None)
        + check_triage(store)
        + check_canonical(store)
    )
    locus = base_locus or relpath
    return [
        finding for finding in _errors(findings)
        if finding.locus == locus or finding.locus.startswith(f"{locus}::")
    ]


def _load_and_validate(root, spec, draft):
    data, findings = load_draft(root, spec, draft)
    if data is None:
        return None, findings
    return data, findings


def _commit(root, spec, data) -> int:
    findings = _preflight(root, spec, data)
    if findings:
        return _fail(findings)
    with paths_module.writer_lock(root):
        target = write_document(root, spec, data)
    print(f"OK: {target.relative_to(Path(root).resolve()).as_posix()}")
    return EXIT_OK
