"""実行記録と会話/ワークスペース排他。stale lock は勝手に除去しない。"""

import json
from contextlib import contextmanager
from dataclasses import asdict
from pathlib import Path

from .conversation_records import validate_record
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
    try:
        lock.mkdir(exist_ok=False)
    except FileExistsError:
        raise ValueError("workspace_busy") from None
    try:
        yield
    finally:
        lock.rmdir()


def save_record(root: Path, request: Request, result: Result) -> None:
    data = asdict(result) | {"workspace": str(request.workspace.resolve())}
    encoded = json.dumps(data, ensure_ascii=False)
    run_dir = root / result.run_id
    result_path = run_dir / "result.json"
    result_path.write_text(encoded, encoding="utf-8")
    result_path.chmod(0o600)
    identities = {result.conversation_id, request.conversation} - {None}
    for identity in identities:
        if valid_id(identity):
            path = root / f"conversation-{identity}.json"
            if path.is_symlink():
                raise ValueError("conversation_record_symlink")
            path.write_text(encoded, encoding="utf-8")
            path.chmod(0o600)
