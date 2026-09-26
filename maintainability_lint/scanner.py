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
        "schema_version": 1,
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
        for key in sorted(set(expected_entries) - set(actual_entries)):
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
    report = scan(root, empty_baseline())
    baseline = empty_baseline()
    for finding in report.findings:
        if finding.rule == "module-over-100-lines":
            baseline["module_lines"][finding.path] = int(finding.detail.split()[0])
        elif finding.rule == "comment-over-3-lines":
            blocks = baseline["comment_blocks"]
            blocks[finding.baseline_key] = blocks.get(finding.baseline_key, 0) + 1
    for path in implementation_python_files(root):
        _, observed = inspect_class_separation(root, path, {})
        baseline["mixed_class_files"].update(observed)
    return baseline
