"""dsv2.rename — slug 改題（yaml＋同名本文の改名＋全 referrer の edges[].to 一括張替え）。"""

import unittest

from dsv2 import meta, rename

from tests.unit.dsv2_fixtures import make_tree


def _read(root, rel):
    return (root / rel).read_text("utf-8")


class TestRename(unittest.TestCase):
    def setUp(self):
        self.root = make_tree(self)
        self.meta = meta.build_meta(self.root)

    def test_plan_lists_referrers(self):
        plan = rename.plan_rename(self.root, self.meta, "parent-spec", "parent-spec-v2")
        # child-spec が parent-spec を参照している
        self.assertEqual(plan.referrers, ["nodes/02-what/spec/child-spec.yaml"])

    def test_collision_and_missing(self):
        with self.assertRaises(rename.RenameError):
            rename.plan_rename(self.root, self.meta, "parent-spec", "child-spec")  # 衝突
        with self.assertRaises(rename.RenameError):
            rename.plan_rename(self.root, self.meta, "nope", "whatever")  # 未検出

    def test_apply_renames_files_and_retargets(self):
        plan = rename.plan_rename(self.root, self.meta, "parent-spec", "parent-spec-v2")
        rename.apply_rename(self.root, plan)

        # 同名本文がある場合は yaml と md の両方が改名される
        self.assertFalse((self.root / "nodes/02-what/spec/parent-spec.yaml").exists())
        self.assertTrue((self.root / "nodes/02-what/spec/parent-spec-v2.yaml").exists())
        self.assertTrue((self.root / "nodes/02-what/spec/parent-spec-v2.md").exists())

        # referrer の to が張り替わる
        child = _read(self.root, "nodes/02-what/spec/child-spec.yaml")
        self.assertIn('to: "parent-spec-v2"', child)
        self.assertNotIn('to: "parent-spec"', child)

        # 索引を再構築すると新 slug で解決できる
        m2 = meta.build_meta(self.root)
        by_id = meta.index_by_id(m2)
        self.assertIn("parent-spec-v2", by_id)
        self.assertNotIn("parent-spec", by_id)

    def test_no_referrers_note(self):
        plan = rename.plan_rename(self.root, self.meta, "lonely", "lonely-v2")
        self.assertEqual(plan.referrers, [])
        self.assertTrue(plan.notes)

    def test_bodyless_node_renames_yaml_only(self):
        y = self.root / "nodes/04-verification/tc/bodyless.yaml"
        y.parent.mkdir(parents=True, exist_ok=True)
        y.write_text('title: "本文なし"\nversion: "0.1.0"\nedges: []\n', "utf-8")
        m = meta.build_meta(self.root)

        plan = rename.plan_rename(self.root, m, "bodyless", "bodyless-v2")

        self.assertEqual(plan.moves, [
            ("nodes/04-verification/tc/bodyless.yaml",
             "nodes/04-verification/tc/bodyless-v2.yaml"),
        ])

    def test_shared_body_ref_is_not_renamed_with_node(self):
        shared = self.root / "nodes/04-verification/td/shared.md"
        shared.parent.mkdir(parents=True, exist_ok=True)
        shared.write_text("# shared\n", "utf-8")
        y = self.root / "nodes/04-verification/td/td-a.yaml"
        y.write_text('title: "TD A"\nversion: "0.1.0"\n'
                     'body_ref.file: "nodes/04-verification/td/shared.md"\n'
                     'edges: []\n', "utf-8")
        m = meta.build_meta(self.root)

        plan = rename.plan_rename(self.root, m, "td-a", "td-a-v2")

        self.assertEqual(plan.moves, [
            ("nodes/04-verification/td/td-a.yaml",
             "nodes/04-verification/td/td-a-v2.yaml"),
        ])


if __name__ == "__main__":
    unittest.main()
