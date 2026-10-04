"""Include standalone hook tests in the repository's normal unit discovery."""
from pathlib import Path
import unittest


def load_tests(loader, tests, pattern):
    directory = Path(__file__).resolve().parents[1] / "jev_hooks"
    return unittest.TestLoader().discover(str(directory), pattern="test_*.py")
