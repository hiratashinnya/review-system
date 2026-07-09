"""doc-system-v2 validate.py の型別メタデータ検査。"""

from __future__ import annotations

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
        _write(y, 'title: "service run"\nversion: "0.1.0"\n'
                  'source.file: "pkg/mod.py"\n'
                  'source.qualname: "Service.run"\n'
                  'source.kind: method\nedges: []\n')
        msgs = validate.validate_node(y, self.root)
        self.assertFalse([m for m in msgs if m.startswith("ERROR")], msgs)

    def test_src_missing_qualname_is_error(self):
        _write(self.repo / "pkg/mod.py", "def present():\n    pass\n")
        y = self.root / "nodes/06-implementation/src/missing.yaml"
        _write(y, 'title: "missing"\nversion: "0.1.0"\n'
                  'source.file: "pkg/mod.py"\n'
                  'source.qualname: "absent"\n'
                  'source.kind: function\nedges: []\n')
        msgs = validate.validate_node(y, self.root)
        self.assertTrue(any("source.qualname" in m for m in msgs), msgs)

    def test_tc_requires_test_metadata_and_existing_file(self):
        y = self.root / "nodes/04-verification/tc/tc-a.yaml"
        _write(y, 'title: "tc a"\nversion: "0.1.0"\nedges: []\n')
        msgs = validate.validate_node(y, self.root)
        self.assertTrue(any("test.file/test.qualname/test.kind 必須" in m for m in msgs), msgs)

        _write(self.repo / "tests/test_sample.py", "def test_ok():\n    pass\n")
        _write(y, 'title: "tc a"\nversion: "0.1.0"\n'
                  'test.file: "tests/test_sample.py"\n'
                  'test.qualname: "test_ok"\n'
                  'test.kind: pytest\nedges: []\n')
        msgs = validate.validate_node(y, self.root)
        self.assertFalse([m for m in msgs if m.startswith("ERROR")], msgs)


if __name__ == "__main__":
    unittest.main()
