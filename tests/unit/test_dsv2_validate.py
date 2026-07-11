"""doc-system-v2 validate.py の型別メタデータ検査。"""

from __future__ import annotations

import contextlib
import io
import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


def _load_validate():
    path = Path(__file__).resolve().parents[2] / "doc-system-v2" / "validate.py"
    sys.path.insert(0, str(path.parent))
    spec = importlib.util.spec_from_file_location("_dsv2_validate", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


validate = _load_validate()


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, "utf-8")


class TestValidateIdentifierMetadata(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = Path(self.tmp.name)
        self.root = self.repo / "doc-system-v2"
        self.root.mkdir()

    def test_src_python_qualname_exists(self):
        _write(self.repo / "pkg/mod.py", "class Service:\n    def run(self):\n        pass\n")
        y = self.root / "nodes/06-implementation/src/service-run.yaml"
        _write(y, 'title: "service run"\nversion: "0.1.0"\nlabels: []\nscheduled: "sprint-1"\n'
                  'source.file: "pkg/mod.py"\n'
                  'source.qualname: "Service.run"\n'
                  'source.kind: method\nedges: []\n')
        msgs = validate.validate_node(y, self.root)
        self.assertFalse([m for m in msgs if m.startswith("ERROR")], msgs)

    def test_src_missing_qualname_is_error(self):
        _write(self.repo / "pkg/mod.py", "def present():\n    pass\n")
        y = self.root / "nodes/06-implementation/src/missing.yaml"
        _write(y, 'title: "missing"\nversion: "0.1.0"\nlabels: []\nscheduled: "sprint-1"\n'
                  'source.file: "pkg/mod.py"\n'
                  'source.qualname: "absent"\n'
                  'source.kind: function\nedges: []\n')
        msgs = validate.validate_node(y, self.root)
        self.assertTrue(any("source.qualname" in m for m in msgs), msgs)

    def test_tc_requires_test_metadata_and_existing_file(self):
        y = self.root / "nodes/04-verification/tc/tc-a.yaml"
        _write(y, 'title: "tc a"\nversion: "0.1.0"\nlabels: []\nscheduled: "sprint-1"\nedges: []\n')
        msgs = validate.validate_node(y, self.root)
        self.assertTrue(any("test.file/test.qualname/test.kind 必須" in m for m in msgs), msgs)

        _write(self.repo / "tests/test_sample.py", "def test_ok():\n    pass\n")
        _write(y, 'title: "tc a"\nversion: "0.1.0"\nlabels: []\nscheduled: "sprint-1"\n'
                  'test.file: "tests/test_sample.py"\n'
                  'test.qualname: "test_ok"\n'
                  'test.kind: pytest\nedges: []\n')
        msgs = validate.validate_node(y, self.root)
        self.assertFalse([m for m in msgs if m.startswith("ERROR")], msgs)


class TestValidateScheduledRequired(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "doc-system-v2"
        self.root.mkdir()

    def test_empty_scheduled_is_error(self):
        y = self.root / "nodes/02-what/spec/empty-scheduled.yaml"
        _write(y, 'title: "empty scheduled"\nversion: "0.1.0"\n'
                  "labels: []\n"
                  'scheduled: ""\n'
                  "edges: []\n")
        _write(y.with_suffix(".md"), "body\n")

        msgs = validate.validate_node(y, self.root)

        self.assertIn("ERROR: scheduled が空", msgs)


class TestValidateExactLinkCounts(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = Path(self.tmp.name)
        self.root = self.repo / "doc-system-v2"
        self.root.mkdir()
        _write(self.repo / "tests/test_sample.py", "def test_a():\n    pass\n\ndef test_b():\n    pass\n")
        _write(
            self.root / "config.yml",
            "exact_link_counts:\n"
            "  - { node: td, direction: incoming, peer: tc, count: 1, activate_stage: verification, severity: error, reason: \"TDはちょうど1つのTC\" }\n"
            "  - { node: tc, direction: outgoing, peer: td, count: 1, activate_stage: verification, severity: error, reason: \"TCはちょうど1つのTD\" }\n",
        )

    def _write_td(self, name: str) -> None:
        y = self.root / f"nodes/04-verification/td/{name}.yaml"
        _write(y, f'title: "{name}"\nversion: "0.1.0"\nlabels: []\nscheduled: "sprint-1"\nedges: []\n')
        _write(y.with_suffix(".md"), f"# {name}\n")

    def _write_tc(self, name: str, qualname: str, edges: str) -> None:
        _write(
            self.root / f"nodes/04-verification/tc/{name}.yaml",
            f'title: "{name}"\nversion: "0.1.0"\nlabels: []\nscheduled: "sprint-1"\n'
            'test.file: "tests/test_sample.py"\n'
            f'test.qualname: "{qualname}"\n'
            "test.kind: pytest\n"
            "edges:\n"
            f"{edges}",
        )

    def _run_validate(self) -> tuple[int, str]:
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = validate.main(["validate.py", str(self.root)])
        return code, out.getvalue()

    def test_main_reports_exact_link_count_violation(self):
        self._write_td("td-a")
        self._write_tc("tc-a", "test_a", "  - to: td-a\n    ref_version: \"0.1\"\n")
        self._write_tc("tc-b", "test_b", "  - to: td-a\n    ref_version: \"0.1\"\n")

        code, stdout = self._run_validate()

        self.assertEqual(code, 1, stdout)
        self.assertIn("[NG] exact_link_counts", stdout)
        self.assertIn("td-a (td) incoming tc expected=1 actual=2", stdout)

    def test_main_accepts_td_tc_one_to_one(self):
        self._write_td("td-a")
        self._write_tc("tc-a", "test_a", "  - to: td-a\n    ref_version: \"0.1\"\n")

        code, stdout = self._run_validate()

        self.assertEqual(code, 0, stdout)
        self.assertNotIn("exact_link_counts", stdout)


class TestFindOrphanMds(unittest.TestCase):
    """issue #183: .yaml 起点の走査（main）で不可視になっていた孤立 .md の検出。"""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "doc-system-v2"
        self.root.mkdir()

    def _write(self, rel: str, text: str) -> Path:
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, "utf-8")
        return p

    def _run_validate(self) -> tuple[int, str]:
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = validate.main(["validate.py", str(self.root)])
        return code, out.getvalue()

    def test_orphan_md_without_yaml_is_detected(self):
        self._write(
            "nodes/02-what/spec/x.yaml",
            'title: "x"\nversion: "0.1.0"\nlabels: []\nscheduled: "sprint-1"\nedges: []\n',
        )
        self._write("nodes/02-what/spec/x.md", "body\n")
        orphan = self._write("nodes/02-what/spec/stray.md", "誰にも参照されない本文\n")

        errs = validate.find_orphan_mds(self.root)

        self.assertEqual(errs, [f"ERROR: サイドカー欠落: {orphan.relative_to(self.root)}"])

    def test_body_ref_referenced_md_is_not_orphan(self):
        self._write("nodes/04-verification/td/shared.md", "# shared\n")
        self._write(
            "nodes/04-verification/td/x.yaml",
            'title: "x"\nversion: "0.1.0"\nlabels: []\nscheduled: "sprint-1"\n'
            'body_ref.file: "nodes/04-verification/td/shared.md"\n'
            "edges: []\n",
        )

        errs = validate.find_orphan_mds(self.root)

        self.assertEqual(errs, [])

    def test_main_reports_orphan_md_and_nonzero_exit(self):
        self._write(
            "nodes/02-what/spec/x.yaml",
            'title: "x"\nversion: "0.1.0"\nlabels: []\nscheduled: "sprint-1"\nedges: []\n',
        )
        self._write("nodes/02-what/spec/x.md", "body\n")
        self._write("nodes/02-what/spec/stray.md", "誰にも参照されない本文\n")

        code, stdout = self._run_validate()

        self.assertEqual(code, 1, stdout)
        self.assertIn("orphan .md（yaml サイドカー欠落）", stdout)
        self.assertIn("stray.md", stdout)

    def test_main_no_orphan_when_corpus_clean(self):
        self._write(
            "nodes/02-what/spec/x.yaml",
            'title: "x"\nversion: "0.1.0"\nlabels: []\nscheduled: "sprint-1"\nedges: []\n',
        )
        self._write("nodes/02-what/spec/x.md", "body\n")

        code, stdout = self._run_validate()

        self.assertEqual(code, 0, stdout)
        self.assertNotIn("orphan .md", stdout)


if __name__ == "__main__":
    unittest.main()
