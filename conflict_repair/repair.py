"""生成対象と正本を検証し、安全な場合だけマージ結果を生成する。"""
import stat
from pathlib import Path

from guidance_sync.filesystem import check, render
from guidance_sync.rendering import _source_dependency_errors, rendered_bytes
from guidance_sync.sources import COMMON_SOURCE, PRINCIPLES_SOURCE, TARGETS

from . import git


def regular_path(root, relative, missing=False):
    path = root
    for part in Path(relative).parts:
        path = path / part
        try:
            mode = path.lstat().st_mode
        except FileNotFoundError:
            if missing and path == root / relative:
                return
            raise ValueError(f'ファイルがありません: {relative}')
        if stat.S_ISLNK(mode):
            raise ValueError(f'symlink は使用できません: {relative}')
    if not stat.S_ISREG(mode):
        raise ValueError(f'通常ファイルではありません: {relative}')


def regenerate(repo, merge_result):
    unresolved = git.conflicts(repo)
    if unresolved - TARGETS.keys():
        raise ValueError(f'登録外の競合: {sorted(unresolved)}')
    if merge_result.returncode and not unresolved:
        raise ValueError('git merge に失敗')
    inputs = {COMMON_SOURCE, PRINCIPLES_SOURCE, *TARGETS.values()}
    for path in inputs:
        regular_path(repo, path)
    for path in TARGETS:
        regular_path(repo, path, missing=path in unresolved)
    load = lambda path: (repo / path).read_bytes()
    errors = _source_dependency_errors(load=load)
    if errors:
        raise ValueError('; '.join(errors))
    drift = bool(unresolved) or any(load(path) != rendered_bytes(path, load=load)
                                   for path in TARGETS)
    if not drift:
        return False
    render(repo)
    errors = check(repo)
    if errors:
        raise ValueError('; '.join(errors))
    return True
