"""台帳 Store の値オブジェクトと公開 API。"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from . import paths as paths_module
from .model import Finding
from .schema import DocSpec


@dataclass(frozen=True)
class Document:
    kind: str
    document_id: str
    relpath: str
    path: Path
    data: dict
    text: str


@dataclass
class Store:
    root: Path
    documents: dict
    findings: list

    def of(self, kind: str) -> list[Document]:
        return self.documents.get(kind, [])

    def by_id(self, kind: str, document_id: str) -> Document | None:
        for document in self.of(kind):
            if document.document_id == document_id:
                return document
        return None

    def ids(self, kind: str) -> set[str]:
        return {document.document_id for document in self.of(kind)}


def _relpath(root: Path, path: Path) -> str:
    return path.resolve().relative_to(Path(root).resolve()).as_posix()


def _duplicate_ids(documents: list[Document]) -> list[str]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for document in documents:
        if document.document_id in seen:
            duplicates.add(document.document_id)
        seen.add(document.document_id)
    return sorted(duplicates)


def load_store(root) -> Store:
    """保存済み文書を読み込み、文書検証の findings を集める。"""
    from .store_load import load_store as implementation

    return implementation(root)


def canonical_text(spec: DocSpec, data: dict) -> str:
    from .store_document_io import canonical_text as implementation

    return implementation(spec, data)


def load_draft(root, spec: DocSpec, draft) -> tuple[dict | None, list[Finding]]:
    """CLI 書込み前に draft を読み、正規化する。"""
    from .store_document_io import load_draft as implementation

    return implementation(root, spec, draft)


def write_document(root, spec: DocSpec, data: dict) -> Path:
    """canonical 文書を書き、読み戻し結果を検証する。"""
    from .store_document_io import write_document as implementation

    return implementation(root, spec, data)
