"""別git作業面とsymlinkを越えず現在repoの成果物directoryを探す。"""
import os
from pathlib import Path


def artifact_directories(repo, names):
    root = Path(repo).resolve()
    found = []
    for current, children, _ in os.walk(root, followlinks=False):
        directory = Path(current)
        marker = directory / ".git"
        if directory != root and (marker.exists() or marker.is_symlink()):
            children[:] = []
            continue
        children[:] = [name for name in children if name != ".git"]
        if directory != root and directory.name in names:
            found.append(directory)
        for name in children:
            candidate = directory / name
            if name in names and candidate.is_symlink():
                raise ValueError(f"artifact directoryがsymlink: {candidate}")
    return sorted(found)
