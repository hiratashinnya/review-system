"""保存済み台帳文書を Store へ読み込み、検証 findings を集める。"""

from pathlib import Path

from . import paths as paths_module
from .model import (
    DocumentError,
    Finding,
    check_document_identity,
    normalize_document,
    parse_toml,
)
from .schema import SPECS, filename_for
from .store import Document, Store, _duplicate_ids, _relpath


def load_store(root) -> Store:
    """3種の文書を読み込む。不在のディレクトリだけ空として扱う。"""
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
        for document_id in _duplicate_ids(collected):
            findings.append(Finding(
                "L1", "ERROR", f".ai/feedback/{spec.subdir}",
                f"id が重複している: {document_id}",
            ))
        documents[kind] = collected
    return Store(root=root, documents=documents, findings=findings)
