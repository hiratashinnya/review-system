"""dsv2.cleantmp — tmp 著作ミラーの安全削除（ガード付き・reconciliation Step 3-3）。

境界値：``tmp/_handoff`` は拒否／``tmp/`` の外は拒否／階層違いは拒否／正常系は削除される。
"""

import tempfile
import unittest
from pathlib import Path

from dsv2 import cleantmp
from dsv2.cli import EXIT_ERROR, EXIT_NOT_FOUND, EXIT_OK, main


def _make_repo(case) -> Path:
    """``tmp/sprint-1/parent-a`` と ``tmp/_handoff`` を持つ疑似リポジトリを作る。"""
    root = Path(tempfile.mkdtemp(prefix="cleantmp-")).resolve()
    case.addCleanup(lambda: __import__("shutil").rmtree(root, ignore_errors=True))
    target = root / "tmp" / "sprint-1" / "parent-a" / "nodes" / "02-spec" / "spec"
    target.mkdir(parents=True)
    (target / "some-slug.md").write_text("# SPEC\n", encoding="utf-8")
    (target / "some-slug.yaml").write_text('title: "x"\n', encoding="utf-8")
    handoff = root / "tmp" / "_handoff"
    handoff.mkdir(parents=True)
    (handoff / "spec-author--parent-a.yaml").write_text("agent: spec-author\n", encoding="utf-8")
    (root / "doc-system-v2" / "nodes").mkdir(parents=True)
    return root


class TestPlanGuards(unittest.TestCase):
    def setUp(self):
        self.root = _make_repo(self)

    def test_plan_accepts_sprint_parent_dir(self):
        plan = cleantmp.plan_clean(self.root / "tmp/sprint-1/parent-a", self.root)
        self.assertEqual(plan.target, (self.root / "tmp/sprint-1/parent-a").resolve())
        self.assertEqual(plan.files, 2)
        self.assertEqual(plan.rel, "tmp/sprint-1/parent-a")

    def test_rejects_handoff_dir(self):
        with self.assertRaises(cleantmp.CleanTmpError) as ctx:
            cleantmp.plan_clean(self.root / "tmp/_handoff", self.root)
        self.assertIn("_handoff", str(ctx.exception))
        self.assertTrue((self.root / "tmp/_handoff").is_dir())

    def test_rejects_path_under_handoff(self):
        (self.root / "tmp/_handoff/sub").mkdir()
        with self.assertRaises(cleantmp.CleanTmpError) as ctx:
            cleantmp.plan_clean(self.root / "tmp/_handoff/sub", self.root)
        self.assertIn("_handoff", str(ctx.exception))

    def test_rejects_outside_tmp(self):
        with self.assertRaises(cleantmp.CleanTmpError) as ctx:
            cleantmp.plan_clean(self.root / "doc-system-v2/nodes", self.root)
        self.assertIn("tmp/ の外", str(ctx.exception))

    def test_rejects_parent_escape(self):
        with self.assertRaises(cleantmp.CleanTmpError):
            cleantmp.plan_clean(self.root / "tmp/sprint-1/../../doc-system-v2", self.root)

    def test_rejects_tmp_root_itself(self):
        with self.assertRaises(cleantmp.CleanTmpError):
            cleantmp.plan_clean(self.root / "tmp", self.root)

    def test_rejects_wrong_depth(self):
        with self.assertRaises(cleantmp.CleanTmpError):
            cleantmp.plan_clean(self.root / "tmp/sprint-1", self.root)  # 浅い
        with self.assertRaises(cleantmp.CleanTmpError):
            cleantmp.plan_clean(self.root / "tmp/sprint-1/parent-a/nodes", self.root)  # 深い

    def test_rejects_symlink(self):
        link = self.root / "tmp/sprint-1/link-a"
        try:
            link.symlink_to(self.root / "tmp/sprint-1/parent-a")
        except (OSError, NotImplementedError):  # pragma: no cover - symlink 不可環境
            self.skipTest("symlink を作れない環境")
        with self.assertRaises(cleantmp.CleanTmpError) as ctx:
            cleantmp.plan_clean(link, self.root)
        self.assertIn("symlink", str(ctx.exception))

    def test_missing_target_is_not_found(self):
        with self.assertRaises(cleantmp.CleanTmpNotFound):
            cleantmp.plan_clean(self.root / "tmp/sprint-1/no-such-parent", self.root)

    def test_missing_tmp_root_is_error(self):
        bare = Path(tempfile.mkdtemp(prefix="cleantmp-bare-")).resolve()
        self.addCleanup(lambda: __import__("shutil").rmtree(bare, ignore_errors=True))
        with self.assertRaises(cleantmp.CleanTmpError):
            cleantmp.plan_clean(bare / "tmp/sprint-1/parent-a", bare)


class TestApply(unittest.TestCase):
    def setUp(self):
        self.root = _make_repo(self)

    def test_apply_removes_only_target(self):
        plan = cleantmp.plan_clean(self.root / "tmp/sprint-1/parent-a", self.root)
        cleantmp.apply_clean(plan)
        self.assertFalse((self.root / "tmp/sprint-1/parent-a").exists())
        self.assertTrue((self.root / "tmp/_handoff/spec-author--parent-a.yaml").is_file())
        self.assertTrue((self.root / "tmp/sprint-1").is_dir())


class TestCli(unittest.TestCase):
    def setUp(self):
        self.root = _make_repo(self)

    def _run(self, path, *extra):
        return main(["clean-tmp", str(path), "--repo-root", str(self.root), *extra])

    def test_dry_run_keeps_files(self):
        self.assertEqual(self._run(self.root / "tmp/sprint-1/parent-a"), EXIT_OK)
        self.assertTrue((self.root / "tmp/sprint-1/parent-a").is_dir())

    def test_apply_deletes(self):
        self.assertEqual(self._run(self.root / "tmp/sprint-1/parent-a", "--apply"), EXIT_OK)
        self.assertFalse((self.root / "tmp/sprint-1/parent-a").exists())

    def test_handoff_is_rejected_with_exit_error(self):
        self.assertEqual(self._run(self.root / "tmp/_handoff", "--apply"), EXIT_ERROR)
        self.assertTrue((self.root / "tmp/_handoff").is_dir())

    def test_outside_tmp_is_rejected_with_exit_error(self):
        self.assertEqual(self._run(self.root / "doc-system-v2/nodes", "--apply"), EXIT_ERROR)
        self.assertTrue((self.root / "doc-system-v2/nodes").is_dir())

    def test_missing_target_exit_not_found(self):
        self.assertEqual(self._run(self.root / "tmp/sprint-1/nope", "--apply"), EXIT_NOT_FOUND)


if __name__ == "__main__":
    unittest.main()
