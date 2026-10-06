"""Find unprotected Python date and epoch literals across the CI test roots."""
from pathlib import Path
from .allowlist import is_allowlisted
from .model import Finding
from .test_files import _iter_python_test_files
from .field_values import _field_hits_in_line
from .protection import _build_graph, _is_protected
from .patterns import RELATIVE_TIME_RE, SUSPICIOUS_FIELD_RE, ABS_DATE_VALUE_RE, EPOCH_VALUE_RE, BARE_EPOCH_ASSIGN_RE

def scan_python_literals(root: Path) -> list[Finding]:
    """tests/{unit,jev_hooks,time_fixture_lint}/test_*.py の疑わしいフィールド/epochを検査する。"""
    findings: list[Finding] = []
    for py_path in _iter_python_test_files(root):
        rel = py_path.relative_to(root).as_posix()
        text = py_path.read_text(encoding="utf-8")
        lines = text.splitlines()
        graph = _build_graph(text)

        candidates: dict[str, list[int]] = {}
        for line_no, line in enumerate(lines, 1):
            if RELATIVE_TIME_RE.search(line):
                continue  # time.time() ± offset の相対式は安全（#302 のパターン）
            for name, value in _field_hits_in_line(line):
                if SUSPICIOUS_FIELD_RE.search(name) and (
                    ABS_DATE_VALUE_RE.match(value) or EPOCH_VALUE_RE.match(value)
                ):
                    candidates.setdefault(name, []).append(line_no)
            m2 = BARE_EPOCH_ASSIGN_RE.match(line)
            if m2:
                candidates.setdefault(m2.group(1), []).append(line_no)

        for name, line_nos in sorted(candidates.items()):
            allow = is_allowlisted(rel, name)
            first_line = line_nos[0]
            sample_value = lines[first_line - 1].strip()
            if allow is not None:
                findings.append(Finding(rel, first_line, name, sample_value, "allowlisted", allow.reason))
                continue
            protected = all(_is_protected(graph, text, ln) for ln in line_nos)
            if protected:
                findings.append(Finding(
                    rel, first_line, name, sample_value, "protected",
                    f"参照箇所（関数スコープで確認、{len(line_nos)}箇所で同名ヒット）に clock 保護マーカーあり。",
                ))
            else:
                findings.append(Finding(
                    rel, first_line, name, sample_value, "violation",
                    "clock 保護マーカー（同一スコープ内、clock 関連対象への patch に限る）も"
                    f"time.time() 相対化も無いまま固定値を使用（{len(line_nos)}箇所で同名ヒット）。"
                    "allowlist で inert と示すか、clock を制御すること。",
                ))
    return findings
