"""Public time fixture scanner API; design rationale is in scanner-rationale.md."""
from pathlib import Path
from .model import Finding, Report
from .fixture_scanner import scan_fixtures
from .literal_scanner import scan_python_literals


def scan(root: Path) -> Report:
    return Report(findings=scan_fixtures(root) + scan_python_literals(root))
