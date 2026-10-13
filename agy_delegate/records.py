"""実行記録と会話/ワークスペース排他。stale lock は勝手に除去しない。"""

import json
import os
import time
from contextlib import contextmanager
from dataclasses import asdict
from pathlib import Path

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
    record = root / f"conversation-{request.conversation}.json"
    if record.is_symlink():
        raise ValueError("conversation_record_symlink")
    try:
        data = load_json(record.read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeError):
        raise ValueError("conversation_record_missing_or_invalid") from None
    validate_record(data, str(request.workspace.resolve()), request.conversation)


@contextmanager
def execution_lock(root: Path):
    """内部書込の読取申告に依存しないよう、全実行を workspace 単位で直列化。"""
    lock = root / "workspace.lock"
    deadline = time.monotonic() + 10
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
    data = asdict(result) | {"workspace": str(request.workspace.resolve())}
    encoded = json.dumps(data, ensure_ascii=False)
    run_dir = root / result.run_id
    result_path = run_dir / "result.json"
    _private_write(result_path, encoded)
    identities = {result.conversation_id, request.conversation} - {None}
    for identity in identities:
        if valid_id(identity):
            path = root / f"conversation-{identity}.json"
            if path.is_symlink():
                raise ValueError("conversation_record_symlink")
            summary = {name: data[name] for name in RECORD_TYPES}
            _private_write(path, json.dumps(summary, ensure_ascii=False))


def _private_write(path: Path, encoded: str) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW
    descriptor = os.open(path, flags, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
        os.fchmod(stream.fileno(), 0o600)
        stream.write(encoded)
