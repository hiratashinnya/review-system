"""DS5 フィードバック蓄積（append-only JSONL）。design/05・DD4。MVP は最小。"""
from __future__ import annotations

import json
from pathlib import Path


def append_feedback(store_path: Path, review_id: str, items: list[dict]) -> int:
    """{review_id, finding_id, decision} を1行ずつ追記。追記件数を返す。"""
    store_path.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with store_path.open("a", encoding="utf-8") as fh:
        for it in items:
            fh.write(json.dumps(
                {"review_id": review_id, "finding_id": it["finding_id"], "decision": it["decision"]},
                ensure_ascii=False) + "\n")
            n += 1
    return n


def load_feedback(store_path: Path) -> list[dict]:
    if not store_path.exists():
        return []
    return [json.loads(ln) for ln in store_path.read_text(encoding="utf-8").splitlines() if ln.strip()]
