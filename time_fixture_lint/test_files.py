"""Explicit CI discovery roots and existing fixture paths."""
from pathlib import Path
from .patterns import FIXTURE_ROOT, FIXTURE_EXTS, PY_TEST_ROOTS

def _iter_fixture_files(root: Path) -> list[Path]:
    fixtures_dir = root / FIXTURE_ROOT
    if not fixtures_dir.is_dir():
        return []
    return sorted(p for p in fixtures_dir.rglob("*") if p.is_file() and p.suffix in FIXTURE_EXTS)


def _iter_python_test_files(root: Path) -> list[Path]:
    return sorted(
        path for directory in PY_TEST_ROOTS
        for path in (root / directory).glob("test_*.py")
    )
