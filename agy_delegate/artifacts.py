"""返却 ID の画像だけを、過去ファイルと symlink を除いて回収する。"""

import hashlib
import shutil
from pathlib import Path

from .results import valid_id

IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}


def image_snapshot(brain: Path, conversation: str | None) -> dict:
    """取得元 brain と会話ディレクトリの同一性を記録し、回収時の差し替え検知に使う。"""
    if not brain.is_dir() or brain.is_symlink():
        raise ValueError("brain_invalid")
    identity = {"brain": _identity(brain)}
    if conversation is None:
        return identity | {"existing": {p.name for p in brain.iterdir()}}
    source = _conversation_dir(brain, conversation)
    return identity | {"source": _identity(source) if source.exists() else None,
                       "files": _image_hashes(source)}


def collect_images(brain: Path, conversation: str, before: dict, destination: Path) -> list[str]:
    if "brain" not in before:
        raise ValueError("image_baseline_unavailable")
    if not brain.is_dir() or brain.is_symlink():
        raise ValueError("brain_invalid")
    if before["brain"] != _identity(brain):
        raise ValueError("image_source_replaced")
    source = _conversation_dir(brain, conversation)
    if before.get("source") is not None and (not source.exists() or before["source"] != _identity(source)):
        raise ValueError("image_source_replaced")
    if conversation in before.get("existing", set()):
        raise ValueError("image_baseline_unavailable")
    previous = before.get("files", {})
    changed = [name for name, digest in _image_hashes(source).items() if previous.get(name) != digest]
    if not changed:
        raise ValueError("image_missing")
    destination.mkdir(exist_ok=False)
    paths = []
    for name in changed:
        target = destination / name
        shutil.copyfile(source / name, target)
        paths.append(str(target))
    return paths


def _conversation_dir(brain: Path, conversation: str) -> Path:
    if not valid_id(conversation):
        raise ValueError("conversation_id_invalid")
    source = brain / conversation
    if source.is_symlink() or source.resolve().parent != brain.resolve():
        raise ValueError("image_path_escape")
    return source


def _identity(directory: Path) -> dict:
    info = directory.stat()
    return {"path": str(directory.resolve()), "device": info.st_dev, "inode": info.st_ino}


def _image_hashes(directory: Path) -> dict[str, str]:
    if not directory.exists():
        return {}
    if not directory.is_dir():
        raise ValueError("image_directory_invalid")
    images = {}
    for path in directory.iterdir():
        if path.suffix.lower() in IMAGE_SUFFIXES:
            if path.is_symlink() or not path.is_file():
                raise ValueError("image_symlink_or_nonfile")
            images[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
    return images
