"""Issue #523: owner override の FBK 実在検証と verdict ゲート。

scope 原本の出所は #800/#797 の trusted 記録だけで判定する。
"""
from feedback_ledger.schema import LEDGER_ID_RE
from feedback_ledger.store import load_store

from . import scope_ledger, scope_origin
from .errors import KarteUsageError


def _valid(store, reference):
    return bool(LEDGER_ID_RE.fullmatch(reference) and store.by_id("ledger", reference))


def require_ref(root, reference):
    """書込み前に台帳の実在・ID 形式を確認（存在しなければ fail-close）。"""
    if not _valid(load_store(root), reference):
        raise KarteUsageError(f"override_ref が実在する feedback_ledger entry を指さない: {reference}")


def invalid_refs(root, accepted):
    """ingest-review が台帳を書き始める前に拒否する参照一覧。"""
    refs = {entry.item.override_ref for entry in accepted if entry.item.override_ref}
    if not refs:
        return []
    store = load_store(root)
    return [f"override_ref が実在する feedback_ledger entry を指さない: {ref}"
            for ref in sorted(refs) if not _valid(store, ref)]


def pending(karte, root):
    """finding ID → clean を妨げる理由（既存台帳の読み取りは緩和）。"""
    origins = scope_origin.first_writers(karte.issue, root)
    declared = scope_origin.reviewer_declarations(karte.issue, root)
    owner_scopes = scope_ledger.owner_scopes(karte.issue, root)
    open_items = karte.open_findings()
    refs = {item.override_ref for item in open_items if item.override_ref}
    store = load_store(root) if refs else None
    result = {}
    for item in open_items:
        fid = item.id
        requires = item.disposition == "waived"
        if fid in owner_scopes:
            if fid in declared:
                requires |= owner_scopes[fid] != declared[fid][-1][1]
            elif origins.get(fid) != "main":
                result[fid] = "owner scope に対応する検証済み reviewer 申告原本がない"
                continue
        if requires and not item.override_ref:
            result[fid] = "オーナー判断の override_ref が未記入"
        elif item.override_ref and not _valid(store, item.override_ref):
            result[fid] = "override_ref の参照先が不正または存在しない"
    return result
