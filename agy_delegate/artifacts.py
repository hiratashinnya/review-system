"""返却 ID の画像だけを、過去ファイルと symlink を除いて回収する。"""

import hashlib
import os
from pathlib import Path

from .image_source import fingerprint, held_directory, read_images
from .results import valid_id


def image_snapshot(brain: Path, conversation: str | None) -> dict:
    """取得元 brain と会話ディレクトリの同一性を記録し、回収時の差し替え検知に使う。"""
    with held_directory(brain, "brain_invalid") as brain_fd:
        identity = {"brain": fingerprint(brain_fd)}
        if conversation is None:
            return identity | {"existing": set(os.listdir(brain_fd))}
        with _held_conversation(brain_fd, conversation) as source_fd:
            if source_fd is None:
                return identity | {"source": None, "files": {}}
            return identity | {"source": fingerprint(source_fd), "files": _digests(read_images(source_fd))}


def collect_images(brain: Path, conversation: str, before: dict, destination: Path) -> list[str]:
    """検査した記述子から読んだ同じバイト列でハッシュ比較と書出しを行い、パス再解決を挟まない。"""
    if "brain" not in before:
        raise ValueError("image_baseline_unavailable")
    with held_directory(brain, "brain_invalid") as brain_fd:
        if before["brain"] != fingerprint(brain_fd):
            raise ValueError("image_source_replaced")
        with _held_conversation(brain_fd, conversation) as source_fd:
            recorded = before.get("source")
            if recorded is not None and (source_fd is None or recorded != fingerprint(source_fd)):
                raise ValueError("image_source_replaced")
            if conversation in before.get("existing", set()):
                raise ValueError("image_baseline_unavailable")
            images = read_images(source_fd) if source_fd is not None else {}
    previous = before.get("files", {})
    changed = {name: data for name, data in images.items()
               if previous.get(name) != hashlib.sha256(data).hexdigest()}
    if not changed:
        raise ValueError("image_missing")
    destination.mkdir(exist_ok=False)
    paths = []
    for name, data in changed.items():
        target = destination / name
        with open(target, "xb") as stream:
            stream.write(data)
        paths.append(str(target))
    return paths


def _held_conversation(brain_fd: int, conversation: str):
    if not valid_id(conversation):
        raise ValueError("conversation_id_invalid")
    return held_directory(conversation, "image_path_escape", dir_fd=brain_fd, missing_ok=True)


def _digests(images: dict[str, bytes]) -> dict[str, str]:
    return {name: hashlib.sha256(data).hexdigest() for name, data in images.items()}
