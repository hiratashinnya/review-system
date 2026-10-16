"""ADR/台帳/工程artifactを宣言駆動で導出索引へ接続する。"""
from pathlib import Path
from adr.index import index as adr_index
from adr.schema import ADR_SPEC
from adr.store import load as load_adr
from dsv2.query import deps, dependents, orphans
from harness_trace import adapt_document
from .schema import SPECS
from .store import load


def index(repo):
    root = Path(repo)
    meta = adr_index(root / "adr-records", root)
    for directory in sorted(root.rglob("adr")):
        if directory.is_dir() and ".git" not in directory.parts:
            meta["nodes"].extend(adapt_document(ADR_SPEC, data, path)
                                 for data, path in load_adr(directory))
    meta["nodes"].extend(adapt_document(SPECS[data["artifact_type"]], data, path)
                         for data, path in load(root))
    ids = [node["id"] for node in meta["nodes"]]
    if len(ids) != len(set(ids)):
        raise ValueError("索引内id重複")
    return meta
