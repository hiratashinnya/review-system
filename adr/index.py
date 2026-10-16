"""ADR・台帳と永続 envelope を一つの導出索引へ集約。"""
import json
from pathlib import Path
from feedback_ledger.schema import SPECS
from feedback_ledger.store import load_store
from harness_trace import build_index
from .schema import ADR_SPEC
from .store import load


def index(root, repo, envelope_files=()):
    documents = [(ADR_SPEC, data, path) for data, path in load(root)]
    store = load_store(repo)
    errors = [finding.render() for finding in store.findings if finding.level == "ERROR"]
    if errors:
        raise ValueError("; ".join(errors))
    for kind, spec in SPECS.items():
        documents.extend((spec, doc.data, doc.path) for doc in store.of(kind))
    for filename in envelope_files:
        documents.extend(load_envelope(filename))
    return build_index(documents)


def load_envelope(filename):
    """永続JSON中の DocSpec 宣言を読む。#371 の envelope 本体は規定しない。"""
    from feedback_ledger.schema_types import DocSpec, Field, TableSpec
    import re
    payload = json.loads(Path(filename).read_text(encoding="utf-8"))
    declaration, data = payload["doc_spec"], payload["document"]
    if declaration["kind"] not in ("ChangePlan", "VerificationDesign"):
        raise ValueError("未対応の envelope kind")
    tables = tuple(TableSpec(table["name"], tuple(Field(**field) for field in table["fields"]),
                             table.get("repeated", False)) for table in declaration["tables"])
    spec = DocSpec(declaration["kind"], declaration["schema"], "", re.compile(".+"), tables)
    return [(spec, data, filename)]
