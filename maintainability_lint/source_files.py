"""Issue #539 が対象とする Python 実装ファイルの fail-open しない列挙。"""

import os
from pathlib import Path


EXCLUDED_TOP_LEVEL_DIRS = frozenset(
    {
        ".git",
        "archive",
        "doc-system-v1-archive",
        "doc-system-v2",
        "docs",
        "dsv2",
        "site",
        "tests",
    }
)
PRUNED_DIR_NAMES = frozenset(
    {
        ".abstra", ".cache", ".eggs", ".git", ".hypothesis",
        ".ipynb_checkpoints", ".mypy_cache", ".nox", ".pdm-build", ".pixi",
        ".pybuilder", ".pyre", ".pytest_cache", ".pytype", ".review-state",
        ".review-workspace", ".ruff_cache", ".scrapy", ".serena", ".tox",
        ".venv", ".webassets-cache", ".worktrees", "ENV", "__marimo__",
        "__pypackages__", "__pycache__", "_build", "_site", "activemq-data",
        "build", "cover", "cython_debug", "develop-eggs", "dist", "downloads",
        "eggs", "env", "env.bak", "htmlcov", "instance", "lib", "lib64",
        "mnesia", "node_modules", "parts", "profile_default", "rabbitmq",
        "rabbitmq-data", "sdist", "target", "tmp", "var", "venv", "venv.bak",
        "wheels",
    }
)
PRUNED_REPO_PATHS = frozenset(
    {".claude/worktrees", "marimo/_lsp", "marimo/_static", "share/python-wheels"}
)


def _is_pruned_directory(repo_root: Path, path: Path) -> bool:
    relative = path.relative_to(repo_root).as_posix()
    return (
        path.is_symlink()
        or path.name in PRUNED_DIR_NAMES
        or path.name.endswith(".egg-info")
        or relative in PRUNED_REPO_PATHS
    )


def _python_files_under(repo_root: Path, source_root: Path) -> list[Path]:
    files: list[Path] = []
    for directory, dirnames, filenames in os.walk(source_root):
        current = Path(directory)
        dirnames[:] = sorted(
            name for name in dirnames
            if not _is_pruned_directory(repo_root, current / name)
        )
        for name in filenames:
            candidate = current / name
            if name.endswith(".py") and not candidate.is_symlink():
                files.append(candidate)
    return files


def implementation_python_files(root: Path) -> list[Path]:
    files = [path for path in root.glob("*.py") if not path.is_symlink()]
    for child in root.iterdir():
        if (
            child.name not in EXCLUDED_TOP_LEVEL_DIRS
            and not _is_pruned_directory(root, child)
            and child.is_dir()
        ):
            files.extend(_python_files_under(root, child))
    return sorted(files)
