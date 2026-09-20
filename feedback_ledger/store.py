"""`.ai/feedback/` 配下の文書の読み書き（CLI と check が共有する唯一の入口）。

書込みは必ず :func:`write_document` を通す。この関数は **canonical 化 → 書込み → 読み戻し →
再正規化して一致確認**までを1回でやる（ラウンドトリップの自己検証）。自前シリアライザを
持つ以上「書けたが読み戻せない／読み戻すと値が変わる」バグは静かに台帳を壊すので、
書いた側で必ず確かめる。

依存仕様: Issue #522「提案挙動」1〜3。
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from . import paths as paths_module
from .model import (
    DocumentError,
    Finding,
    check_document_identity,
    normalize_document,
    parse_toml,
)
from .schema import SPECS, DocSpec, filename_for
from .tomlwrite import dumps


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


def load_store(root) -> Store:
    """3種の文書を読み込む。読めない／L1 違反は ``findings`` へ積む（例外にしない）。"""
    root = Path(root)
    documents: dict[str, list[Document]] = {}
    findings: list[Finding] = []
    for kind, spec in SPECS.items():
        collected: list[Document] = []
        try:
            directory = paths_module.subdir(root, spec.subdir)
        except paths_module.FeedbackMissing:
            documents[kind] = collected
            continue
        for path in sorted(directory.glob("*.toml")):
            relative = _relpath(root, path)
            if path.is_symlink():
                findings.append(Finding("L1", "ERROR", relative, "文書が symlink"))
                continue
            text = path.read_text(encoding="utf-8")
            try:
                raw = parse_toml(text)
            except DocumentError as exc:
                findings.append(Finding("L1", "ERROR", relative, str(exc)))
                continue
            data, document_findings = normalize_document(spec, raw, relative)
            findings.extend(document_findings)
            if data is None:
                continue
            findings.extend(check_document_identity(spec, data, relative))
            document_id = data.get("id", "")
            expected = filename_for(spec, document_id)
            if path.name != expected:
                findings.append(Finding(
                    "L1", "ERROR", relative,
                    f"ファイル名が id と一致しない（期待: {expected}）",
                ))
            collected.append(Document(
                kind=kind,
                document_id=document_id,
                relpath=relative,
                path=path,
                data=data,
                text=text,
            ))
        duplicates = _duplicate_ids(collected)
        for document_id in duplicates:
            findings.append(Finding(
                "L1", "ERROR", f".ai/feedback/{spec.subdir}",
                f"id が重複している: {document_id}",
            ))
        documents[kind] = collected
    return Store(root=root, documents=documents, findings=findings)


def _duplicate_ids(documents: list[Document]) -> list[str]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for document in documents:
        if document.document_id in seen:
            duplicates.add(document.document_id)
        seen.add(document.document_id)
    return sorted(duplicates)


def canonical_text(spec: DocSpec, data: dict) -> str:
    return dumps(spec, data)


def load_draft(root, spec: DocSpec, draft) -> tuple[dict | None, list[Finding]]:
    """下書き TOML を読んで正規化する（書込み前の検証に使う）。

    正規化に失敗した下書きでは ``data`` が ``None`` になる（``findings`` に理由が入る）。
    呼び出し側（``cli._load_and_validate``）はこの ``None`` を分岐しており、戻り値の型宣言も
    それに合わせる（F-522-08・型検査ゲートへ登録するための是正）。
    """
    path = paths_module.draft_path(root, draft)
    relative = _relpath(Path(root), path)
    text = paths_module.read_text(path)
    raw = parse_toml(text)
    data, findings = normalize_document(spec, raw, relative)
    if data is not None:
        findings.extend(check_document_identity(spec, data, relative))
    return data, findings


def write_document(root, spec: DocSpec, data: dict) -> Path:
    """canonical 化して書き、**読み戻して一致するか**を確かめてからパスを返す。"""
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
