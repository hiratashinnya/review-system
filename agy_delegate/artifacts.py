"""返却 ID の画像だけを、過去ファイルと symlink を除いて回収する。"""

import hashlib
import shutil
from pathlib import Path

from .results import valid_id

IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}


def image_snapshot(brain: Path, conversation: str | None) -> dict:
    if not brain.is_dir() or brain.is_symlink():
        raise ValueError("brain_invalid")
    if conversation is None:
        return {"existing": {p.name for p in brain.iterdir()}}
    return {"files": _image_hashes(_conversation_dir(brain, conversation))}


def collect_images(brain: Path, conversation: str, before: dict, destination: Path) -> list[str]:
    source = _conversation_dir(brain, conversation)
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
