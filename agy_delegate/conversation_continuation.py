"""継続開始前に旧成功記録を継続不可へ原子的に更新する（成否は起動条件）。"""

import json
import os
from pathlib import Path

from .atomic_record_write import atomic_private_write as _atomic_private_write
from .strict_json import load_json
from .types import Request

IN_PROGRESS_REASON = "conversation_continuation_in_progress"


def mark_continuation_started(root: Path, request: Request) -> None:
    """更新に失敗したら例外を伝播し、呼出元は子プロセスを起動しない。"""
    if request.conversation is None:
        return
    record = root / f"conversation-{request.conversation}.json"
    if record.is_symlink():
        raise ValueError("conversation_record_symlink")
    data = load_json(record.read_text(encoding="utf-8"))
    data["classification"] = "failed"
    data["reasons"] = list(data["reasons"]) + [IN_PROGRESS_REASON]
    _atomic_private_write(record, json.dumps(data, ensure_ascii=False))
