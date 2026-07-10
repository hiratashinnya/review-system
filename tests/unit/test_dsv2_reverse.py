"""dsv2.reverse — FND 辺逆転（forward 削除・backward 付与・DD-3・z バンプ・git mv）。"""

import subprocess
import unittest

from dsv2 import meta, reverse
from dsv2.reverse import DD3_MARKER

from tests.unit.dsv2_fixtures import make_tree


def _read(root, rel):
    return (root / rel).read_text("utf-8")


class TestReversePlan(unittest.TestCase):
    def setUp(self):
        self.root = make_tree(self)
        self.meta = meta.build_meta(self.root)

    def test_plan_classifies_normal_target(self):
        plan = reverse.plan_reverse(self.root, self.meta, "fnd-open")
        self.assertFalse(plan.noop)
        self.assertEqual([a.kind for a in plan.actions], ["normal"])
        self.assertIn(DD3_MARKER, plan.dd3_line)
        self.assertEqual(
            plan.fnd_yaml_new,
            "nodes/04-verification/fnd/resolved/fnd-open.yaml",
        )

    def test_unknown_and_wrong_type(self):
        with self.assertRaises(reverse.ReverseError):
            reverse.plan_reverse(self.root, self.meta, "nope")
        with self.assertRaises(reverse.ReverseError):
            reverse.plan_reverse(self.root, self.meta, "child-spec")  # spec, not fnd


class TestReverseApply(unittest.TestCase):
    def setUp(self):
        self.root = make_tree(self)
        self.meta = meta.build_meta(self.root)

    def test_apply_moves_and_rewrites(self):
        plan = reverse.plan_reverse(self.root, self.meta, "fnd-open")
        reverse.apply_reverse(self.root, plan)

        # git mv: open が消え resolved に出現
        self.assertFalse((self.root / "nodes/04-verification/fnd/open/fnd-open.yaml").exists())
        new_yaml = _read(self.root, "nodes/04-verification/fnd/resolved/fnd-open.yaml")
        self.assertIn("edges: []", new_yaml)
        self.assertIn('version: "0.1.1"', new_yaml)  # z バンプ

        # DD-3 が本文に凍結記録される
        new_md = _read(self.root, "nodes/04-verification/fnd/resolved/fnd-open.md")
        self.assertIn(DD3_MARKER, new_md)

        # 対象 P に backward 辺が付与され z バンプ
        p_yaml = _read(self.root, "nodes/03-analysis/p/target-p.yaml")
        self.assertIn('- to: "fnd-open"', p_yaml)
        self.assertIn('version: "0.2.1"', p_yaml)

        # 移動が git rename として記録される
        out = subprocess.run(
            ["git", "-C", str(self.root), "status", "--porcelain"],
            capture_output=True, text=True, check=True,
        ).stdout
        self.assertIn("R", out)  # rename エントリ

    def test_reverse_is_idempotent_on_backref(self):
        plan = reverse.plan_reverse(self.root, self.meta, "fnd-open")
        reverse.apply_reverse(self.root, plan)
        # P に既に backref がある状態で、手で FND を open に戻して再計画しても二重付与しない
        # （add_edge の冪等性を直接確認）
        from dsv2 import yamledit
        p_lines = _read(self.root, "nodes/03-analysis/p/target-p.yaml").splitlines()
        _new, skipped = yamledit.add_edge(p_lines, "fnd-open", "0.1")
        self.assertTrue(skipped)


class TestReverseProvenanceAndMissing(unittest.TestCase):
    def test_missing_target_records_notarget(self):
        root = make_tree(self)
        # FND の forward を存在しない ID に差し替える
        y = root / "nodes/04-verification/fnd/open/fnd-open.yaml"
        y.write_text(
            'title: "P の指摘（要確認）"\nversion: "0.1.0"\nlabels: []\nscheduled: "sprint-1"\n'
            "edges:\n"
            '  - to: "does-not-exist"\n'
            '    ref_version: "0.1"\n',
            encoding="utf-8",
        )
        m = meta.build_meta(root)
        plan = reverse.plan_reverse(root, m, "fnd-open")
        self.assertEqual([a.kind for a in plan.actions], ["missing"])
        self.assertIn("付与先なし", plan.notarget_line)


if __name__ == "__main__":
    unittest.main()
