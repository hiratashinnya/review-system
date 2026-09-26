"""3つの機械判定を統合し、baseline の stale entry も拒否する。"""

from __future__ import annotations

from pathlib import Path

from .baseline import load_baseline
from .class_separation import inspect_class_separation
from .comment_blocks import inspect_comment_blocks
from .model import Finding, Report
from .module_length import inspect_module_length
from .source_files import implementation_python_files


def empty_baseline() -> dict[str, object]:
    return {
        "schema_version": 2,
        "source": "Issue #539 measured repository state",
        "module_lines": {},
        "comment_blocks": {},
        "mixed_class_files": {},
    }


def _stale_findings(
    baseline: dict[str, object],
    actual: dict[str, object],
) -> list[Finding]:
    findings: list[Finding] = []
    for section in ("module_lines", "comment_blocks", "mixed_class_files"):
        expected_entries = baseline[section]
        actual_entries = actual[section]
        assert isinstance(expected_entries, dict) and isinstance(actual_entries, dict)
        stale_keys = set(expected_entries) - set(actual_entries)
        if section == "comment_blocks":
            stale_keys |= {
                key
                for key, count in expected_entries.items()
                if actual_entries.get(key, 0) < count
            }
        for key in sorted(stale_keys):
            path = key.split("|", 1)[0]
            detail = f"baseline entry {key!r} no longer matches debt; remove or refresh it"
            findings.append(Finding("stale-baseline", path, 1, "violation", detail, key))
    return findings


def scan(root: Path, baseline: dict[str, object] | None = None) -> Report:
    chosen = load_baseline() if baseline is None else baseline
    modules = chosen["module_lines"]
    comments = chosen["comment_blocks"]
    mixed = chosen["mixed_class_files"]
    assert isinstance(modules, dict) and isinstance(comments, dict) and isinstance(mixed, dict)
    actual = empty_baseline()
    findings: list[Finding] = []
    for path in implementation_python_files(root):
        for inspect, expected, section in (
            (inspect_module_length, modules, "module_lines"),
            (inspect_comment_blocks, comments, "comment_blocks"),
            (inspect_class_separation, mixed, "mixed_class_files"),
        ):
            new_findings, observed = inspect(root, path, expected)
            findings.extend(new_findings)
            target = actual[section]
            assert isinstance(target, dict)
            for key, value in observed.items():
                if section == "comment_blocks":
                    target[key] = target.get(key, 0) + value
                else:
                    target[key] = value
    findings.extend(_stale_findings(chosen, actual))
    return Report(findings=findings)


def build_baseline(root: Path) -> dict[str, object]:
    baseline = empty_baseline()
    for path in implementation_python_files(root):
        _, modules = inspect_module_length(root, path, {})
        baseline["module_lines"].update(modules)
        _, comments = inspect_comment_blocks(root, path, {})
        for key, count in comments.items():
            blocks = baseline["comment_blocks"]
            blocks[key] = blocks.get(key, 0) + count
        _, mixed = inspect_class_separation(root, path, {})
        baseline["mixed_class_files"].update(mixed)
    return baseline
