"""FND バックリファレンスの read-only 監査（辺逆転の不整合検出）。

config.yaml ``fnd_lifecycle`` の意味論に対応する不整合を列挙する:
  * resolved だが forward 辺が残置（``must_not_link_to`` 違反・辺逆転未完）
  * resolved だが backward 辺が無い（``must_be_linked_from`` 違反。本文「付与先なし」なら除外）
  * resolved だが本文に DD-3 ``**指摘時 ref_version**:`` 記録が無い
  * open だが対象が既に ``→FND`` backward 辺を保有（forward/backward 同時存在＝辺逆転未完）
  * forward 辺が存在しない ID を指す（dangling）
  * forward 辺の ref_version ドリフト

判定のみで書込はしない。``reverse`` が処置する対象を洗い出す用途。
"""

from __future__ import annotations

from dataclasses import dataclass

from docidx import query
from docidx.model import NodeIndex

from .reverse import DD3_MARKER, PROVENANCE_TYPES


@dataclass(frozen=True)
class Finding:
    fnd_id: str
    severity: str  # "error" | "warning"
    code: str
    message: str
    file: str
    line: int


def check(index: NodeIndex) -> list[Finding]:
    out: list[Finding] = []
    for node in index.nodes:
        if node.type != "FND":
            continue
        fid = node.id
        loc = (node.file, node.line)
        resolved = node.fields.get("resolved") is True
        forward = list(node.edges)
        backrefs = index.dependents.get(fid, ())
        body = node.body or ""

        if resolved and forward:
            tos = ", ".join(e.to for e in forward)
            out.append(Finding(fid, "warning", "resolved-has-forward",
                               f"resolved だが forward 辺が残置: →{tos}", *loc))
        if resolved and not backrefs and "付与先なし" not in body:
            out.append(Finding(fid, "error", "resolved-no-backref",
                               "resolved だが backward 辺（→FND）が無い", *loc))
        if resolved and DD3_MARKER not in body:
            out.append(Finding(fid, "error", "resolved-no-dd3",
                               f"resolved だが本文に '{DD3_MARKER}' 記録が無い（DD-3）", *loc))

        for e in forward:
            target = index.by_id.get(e.to)
            if target is None:
                out.append(Finding(fid, "error", "dangling-forward",
                                   f"forward 辺が存在しない ID を指す: →{e.to}", *loc))
                continue
            if not resolved and fid in index.dependents.get(e.to, ()):
                out.append(Finding(fid, "error", "open-but-backref-exists",
                                   f"open だが対象 {e.to} が既に →{fid} を保有（辺逆転未完）",
                                   *loc))
            if target.type not in PROVENANCE_TYPES and query._drift(index, e.to, e.ref_version):
                out.append(Finding(fid, "warning", "ref-version-drift",
                                   f"forward 辺 →{e.to} の ref_version={e.ref_version} がドリフト",
                                   *loc))
    return out
