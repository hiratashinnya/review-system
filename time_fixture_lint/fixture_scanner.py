"""Require clock protection in every consumer across the CI test roots."""
from pathlib import Path
from .allowlist import is_allowlisted
from .model import Finding
from .test_files import _iter_fixture_files, _iter_python_test_files
from .field_values import _suspicious_fields_in_text, _occurrence_lines
from .protection import _build_graph, _is_protected

def scan_fixtures(root: Path) -> list[Finding]:
    """tests/fixtures/**/*.{yml,yaml,json} の疑わしいフィールドを検査する。"""
    findings: list[Finding] = []
    py_files = _iter_python_test_files(root)
    py_texts = {p: p.read_text(encoding="utf-8") for p in py_files}
    py_graphs = {p: _build_graph(t) for p, t in py_texts.items()}

    for fixture_path in _iter_fixture_files(root):
        rel = fixture_path.relative_to(root).as_posix()
        text = fixture_path.read_text(encoding="utf-8")
        hits = _suspicious_fields_in_text(text)
        if not hits:
            continue

        basenames = {fixture_path.name, fixture_path.stem}
        referencing = [p for p, t in py_texts.items() if any(b in t for b in basenames)]
        ref_rels = [p.relative_to(root).as_posix() for p in referencing]

        for line_no, name, value in hits:
            allow = is_allowlisted(rel, name)
            if allow is not None:
                findings.append(Finding(rel, line_no, name, value, "allowlisted", allow.reason))
                continue
            if not referencing:
                findings.append(Finding(
                    rel, line_no, name, value, "no_consumer",
                    "この fixture を参照する tests/{unit,jev_hooks,time_fixture_lint}/test_*.py が見つからない"
                    "（wall clock 保護の有無を確認できない）。allowlist に登録するか、"
                    "参照テストを追加/名称を合わせること。",
                ))
                continue

            unprotected: list[str] = []
            for p, r in zip(referencing, ref_rels):
                occ_lines = _occurrence_lines(py_texts[p], basenames)
                if not occ_lines or not all(
                    _is_protected(py_graphs[p], py_texts[p], ln) for ln in occ_lines
                ):
                    unprotected.append(r)

            if not unprotected:
                findings.append(Finding(
                    rel, line_no, name, value, "protected",
                    f"参照テスト全て({', '.join(ref_rels)})の参照箇所が clock 保護スコープ内。",
                ))
            else:
                findings.append(Finding(
                    rel, line_no, name, value, "violation",
                    f"参照テスト {', '.join(sorted(set(unprotected)))} の参照箇所（関数スコープで確認）に"
                    "clock 保護マーカー（unittest.mock.patch/freeze_time/now= 注入等、"
                    "clock 関連対象への patch に限る）が見つからない。",
                ))
    return findings
