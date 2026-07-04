"""dsv2 check-slug — 著作 slug のグローバル一意 fail-close 回帰（Sub-D・DD-22・issue #73）。

reconciliation-validator が書込前に走らせる決定論チェック。slug（=id=ファイル名 stem）が
コーパス既存 id と衝突したら EXIT_ERROR で fail-close することを証明する。
"""

import io
import unittest
from contextlib import redirect_stderr, redirect_stdout

from dsv2 import cli, query
from dsv2.meta import build_meta

from tests.unit.dsv2_fixtures import make_tree


class TestSlugCollisionsPure(unittest.TestCase):
    """純関数 query.slug_collisions（CLI 非依存）。"""

    def setUp(self):
        self.meta = build_meta(make_tree(self))

    def test_unique_slug_no_collision(self):
        self.assertEqual(query.slug_collisions(self.meta, ["brand-new-slug"]), {})

    def test_corpus_collision_detected(self):
        # フィクスチャに実在する id（parent-spec）と衝突。
        res = query.slug_collisions(self.meta, ["parent-spec"])
        self.assertIn("parent-spec", res)
        self.assertTrue(res["parent-spec"].startswith("corpus:"))

    def test_batch_collision_detected(self):
        res = query.slug_collisions(self.meta, ["dup", "dup", "ok"])
        self.assertEqual(res["dup"], "batch(x2)")
        self.assertNotIn("ok", res)

    def test_mixed_only_reports_colliding(self):
        res = query.slug_collisions(self.meta, ["child-spec", "fresh"])
        self.assertIn("child-spec", res)   # 既存 id
        self.assertNotIn("fresh", res)


class TestCheckSlugCli(unittest.TestCase):
    """CLI 終了コード（fail-close）。"""

    def setUp(self):
        self.root = make_tree(self)
        self.base = ["--root", str(self.root)]

    def _run(self, argv):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = cli.main(["check-slug", *argv, *self.base])
        return code, out.getvalue(), err.getvalue()

    def test_unique_slug_exit_ok(self):
        code, out, _ = self._run(["a-genuinely-new-node"])
        self.assertEqual(code, cli.EXIT_OK)
        self.assertIn("一意", out)

    def test_collision_fail_close_exit_error(self):
        # REGRESSION: 既存コーパス id と衝突 → fail-close（EXIT_ERROR）。
        code, _, err = self._run(["target-p"])
        self.assertEqual(code, cli.EXIT_ERROR)
        self.assertIn("衝突", err)
        self.assertIn("target-p", err)

    def test_batch_duplicate_fail_close(self):
        code, _, err = self._run(["same", "same"])
        self.assertEqual(code, cli.EXIT_ERROR)
        self.assertIn("batch", err)

    def test_title_slugified_collision_fail_close(self):
        # --title は slugify.py（唯一実装）で正規化してから照合する。
        # フィクスチャ fnd の title「P の指摘（要確認）」→ slug "p-の指摘"…ではなく既存 id を狙う。
        # 既存 id "lonely" と衝突するタイトルを与える。
        code, out, err = self._run(["--title", "lonely"])
        self.assertEqual(code, cli.EXIT_ERROR)
        self.assertIn("slugify", out)
        self.assertIn("lonely", err)

    def test_no_args_usage_error(self):
        code, _, err = self._run([])
        self.assertEqual(code, cli.EXIT_NOT_FOUND)


if __name__ == "__main__":
    unittest.main()
