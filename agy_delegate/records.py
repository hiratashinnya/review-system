"""実行記録と会話/ワークスペース排他。stale lock は勝手に除去しない。"""

import json
import os
import time
from contextlib import contextmanager
from dataclasses import asdict
from pathlib import Path

from .atomic_record_write import atomic_private_write, remove_marker
from .conversation_records import RECORD_TYPES, validate_record
from .results import valid_id
from .strict_json import load_json
from .types import Request, Result


def state_root(workspace: Path) -> Path:
    root = workspace / "tmp" / "agy"
    for path in (workspace / "tmp", root):
        if path.is_symlink():
            raise ValueError("record_path_symlink")
        path.mkdir(exist_ok=True)
    return root


def check_conversation(root: Path, request: Request) -> None:
    if request.conversation is None:
        return
    if not valid_id(request.conversation):
        raise ValueError("conversation_id_invalid")
    marker = root / f"conversation-{request.conversation}.pending"
    if os.path.lexists(marker):
        raise ValueError("conversation_record_unconfirmed")
    record = root / f"conversation-{request.conversation}.json"
    if record.is_symlink():
        raise ValueError("conversation_record_symlink")
    try:
        data = load_json(record.read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeError):
        raise ValueError("conversation_record_missing_or_invalid") from None
    validate_record(data, str(request.workspace.resolve()), request.conversation)


@contextmanager
def execution_lock(root: Path, *, wait_seconds: int = 130):
    """内部書込の読取申告に依存しないよう、全実行を workspace 単位で直列化。"""
    lock = root / "workspace.lock"
    deadline = time.monotonic() + wait_seconds
    while True:
        try:
            lock.mkdir(exist_ok=False)
            break
        except FileExistsError:
            if time.monotonic() >= deadline:
                raise ValueError("workspace_lock_timeout") from None
            time.sleep(0.02)
    try:
        yield
    finally:
        lock.rmdir()


def save_record(root: Path, request: Request, result: Result) -> None:
    """結果の確定置換後に同期が失敗すると成功表示は残り得るが、印で継続を拒否する。"""
    data = asdict(result) | {"workspace": str(request.workspace.resolve())}
    encoded = json.dumps(data, ensure_ascii=False)
    result_path = root / result.run_id / "result.json"
    success = result.classification == "success_candidate"
    initial = data
    if success:
        initial = data | {"classification": "failed", "reasons": result.reasons + ["result_unconfirmed"]}
    _private_write(result_path, json.dumps(initial, ensure_ascii=False))
    markers = []
    identities = {result.conversation_id, request.conversation} - {None}
    for identity in identities:
        if valid_id(identity):
            path = root / f"conversation-{identity}.json"
            if path.is_symlink():
                raise ValueError("conversation_record_symlink")
            summary = {name: data[name] for name in RECORD_TYPES}
            marker = _save_conversation_summary(path, summary)
            if marker is not None:
                markers.append(marker)
    if success:
        _private_write(result_path, encoded)
    for marker in markers:
        remove_marker(marker)


def _save_conversation_summary(path: Path, summary: dict) -> Path | None:
    encoded = json.dumps(summary, ensure_ascii=False)
    marker = path.with_suffix(".pending") if summary["classification"] == "success_candidate" else None
    if marker is not None:
        _private_write(marker, "")
    _private_write(path, encoded)
    return marker


def _private_write(path: Path, encoded: str) -> None:
    atomic_private_write(path, encoded)
