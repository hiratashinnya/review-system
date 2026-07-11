"""doc-system-v2 validate.py の body_policy 契約。"""

import importlib.util
import sys
import unittest
from pathlib import Path


_VALIDATE = Path(__file__).resolve().parents[2] / "doc-system-v2" / "validate.py"
sys.path.insert(0, str(_VALIDATE.parent))
_SPEC = importlib.util.spec_from_file_location("_dsv2_validate", _VALIDATE)
assert _SPEC is not None and _SPEC.loader is not None, (
    f"failed to build import spec for {_VALIDATE}"
)
validate = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(validate)


class TestValidateBodyPolicy(unittest.TestCase):
    def _root(self):
        import tempfile
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        return Path(tmp.name) / "doc-system-v2"

    def _write_yaml(self, root, rel, text):
        y = root / rel
        y.parent.mkdir(parents=True, exist_ok=True)
        y.write_text(text, "utf-8")
        return y

    def test_required_body_missing_is_error(self):
        root = self._root()
        y = self._write_yaml(root, "nodes/02-what/spec/x.yaml",
                             'title: "x"\nversion: "0.1.0"\nlabels: []\nscheduled: "sprint-1"\nedges: []\n')

        msgs = validate.validate_node(y, root)

        self.assertIn("ERROR: 本文 .md 欠落（body_policy=required）: x.md", msgs)

    def test_bodyless_tc_accepts_missing_md(self):
        root = self._root()
        test_file = root.parent / "tests/test_x.py"
        test_file.parent.mkdir(parents=True, exist_ok=True)
        test_file.write_text("def test_x():\n    pass\n", "utf-8")
        y = self._write_yaml(root, "nodes/04-verification/tc/x.yaml",
                             'title: "x"\nversion: "0.1.0"\nlabels: []\nscheduled: "sprint-1"\n'
                             'test.file: "tests/test_x.py"\n'
                             'test.qualname: "test_x"\n'
                             'test.kind: pytest\nedges: []\n')

        msgs = validate.validate_node(y, root)

        self.assertFalse([m for m in msgs if m.startswith("ERROR")])

    def test_shared_td_accepts_body_ref(self):
        root = self._root()
        shared = root / "nodes/04-verification/td/shared.md"
        shared.parent.mkdir(parents=True, exist_ok=True)
        shared.write_text("# shared\n", "utf-8")
        y = self._write_yaml(root, "nodes/04-verification/td/x.yaml",
                             'title: "x"\nversion: "0.1.0"\nlabels: []\nscheduled: "sprint-1"\n'
                             'body_ref.file: "nodes/04-verification/td/shared.md"\n'
                             'edges: []\n')

        msgs = validate.validate_node(y, root)

        self.assertFalse([m for m in msgs if m.startswith("ERROR")])


if __name__ == "__main__":
    unittest.main()
