"""docidx CLI / build_index の E2E（実物の doc-system ツリーに対して）。"""

import io
import json
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from docidx import cli, scan

REPO_ROOT = Path(__file__).resolve().parents[2]


class TestRealTree(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.index = scan.build_index(repo_root=REPO_ROOT)

    def test_parses_many_nodes_without_errors(self):
        self.assertGreater(len(self.index.nodes), 100)
        errs = [n for n in self.index.nodes if n.parse_error]
        self.assertEqual(errs, [], f"parse errors: {[(n.id, n.parse_error) for n in errs]}")

    def test_ids_unique_and_wellformed(self):
        import re
        ids = [n.id for n in self.index.nodes]
        self.assertEqual(len(ids), len(set(ids)), "重複 ID あり")
        bad = [i for i in ids if not re.fullmatch(r"[A-Z]+(-\d+)+", i)]
        self.assertEqual(bad, [])

    def test_fr1_present_with_edges(self):
        fr1 = self.index.by_id.get("FR-1")
        self.assertIsNotNone(fr1)
        self.assertEqual(fr1.type, "FR")
        self.assertTrue(fr1.edges)

    def test_spec_hierarchy_children_present(self):
        for nid in ("SPEC-1", "SPEC-1-1", "SPEC-1-2"):
            self.assertIn(nid, self.index.by_id)


class TestCliMain(unittest.TestCase):
    def _run(self, argv):
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = cli.main(["--root", str(REPO_ROOT), *argv])
        return code, buf.getvalue()

    def test_index_json_is_valid(self):
        code, out = self._run(["index"])
        self.assertEqual(code, 0)
        data = json.loads(out)
        self.assertTrue(any(n["id"] == "FR-1" for n in data))

    def test_show_json(self):
        code, out = self._run(["show", "FR-1"])
        self.assertEqual(code, 0)
        data = json.loads(out)
        self.assertEqual(data[0]["id"], "FR-1")
        self.assertIn("body", data[0])

    def test_show_missing_returns_2(self):
        code, _ = self._run(["show", "NOPE-999"])
        self.assertEqual(code, cli.EXIT_NOT_FOUND)

    def test_deps_json(self):
        code, out = self._run(["deps", "SPEC-1-1"])
        self.assertEqual(code, 0)
        data = json.loads(out)
        self.assertEqual(data["id"], "SPEC-1-1")
        self.assertTrue(all("drift" in r for r in data["deps"]))

    def test_dependents_json(self):
        code, out = self._run(["dependents", "FR-1"])
        self.assertEqual(code, 0)
        data = json.loads(out)
        self.assertTrue(len(data["dependents"]) > 0)

    def test_search_by_type(self):
        code, out = self._run(["search", "--type", "FND"])
        self.assertEqual(code, 0)
        data = json.loads(out)
        self.assertTrue(all(n["type"] == "FND" for n in data))


if __name__ == "__main__":
    unittest.main()
