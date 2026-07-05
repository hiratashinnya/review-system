"""dsv2 check-slug — 著作 slug のグローバル一意 fail-close 回帰（Sub-D・DD-22・issue #73）。

reconciliation-validator が書込前に走らせる決定論チェック。slug（=id=ファイル名 stem）が
コーパス既存 id と衝突したら EXIT_ERROR で fail-close することを証明する。
"""

import io
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

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

    # --- 更新宣言による corpus 衝突除外（issue #97・案A） ---
    def test_declared_update_excluded_from_corpus(self):
        # 既存 id を「更新」として宣言すると corpus 衝突から除外される。
        res = query.slug_collisions(self.meta, ["parent-spec"], {"parent-spec"})
        self.assertEqual(res, {})

    def test_undeclared_corpus_still_collides(self):
        # 別の既存 id は宣言されていないので従来どおり corpus 衝突。
        res = query.slug_collisions(self.meta, ["parent-spec", "child-spec"], {"parent-spec"})
        self.assertNotIn("parent-spec", res)
        self.assertIn("child-spec", res)
        self.assertTrue(res["child-spec"].startswith("corpus:"))

    def test_batch_dup_fails_even_when_declared(self):
        # 宣言しても batch 内重複は fail-close を維持する。
        res = query.slug_collisions(self.meta, ["parent-spec", "parent-spec"], {"parent-spec"})
        self.assertEqual(res.get("parent-spec"), "batch(x2)")

    def test_declared_update_for_new_slug_is_noop(self):
        # コーパスに無い slug を宣言しても副作用なし（一意なら衝突なし）。
        res = query.slug_collisions(self.meta, ["brand-new"], {"brand-new"})
        self.assertEqual(res, {})

    # --- update_slugs_not_in_corpus（--update typo ハードニング・issue #103 Part B） ---
    def test_update_slugs_not_in_corpus_reports_missing(self):
        res = query.update_slugs_not_in_corpus(self.meta, {"target-p", "no-such-slug"})
        self.assertEqual(res, ["no-such-slug"])

    def test_update_slugs_not_in_corpus_all_present(self):
        res = query.update_slugs_not_in_corpus(self.meta, {"target-p", "parent-spec"})
        self.assertEqual(res, [])

    def test_update_slugs_not_in_corpus_empty_declaration(self):
        self.assertEqual(query.update_slugs_not_in_corpus(self.meta, set()), [])


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

    # --- --from-dir（tmp ミラー走査・issue #89） ---
    def _mirror(self, *stems):
        d = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: __import__("shutil").rmtree(d, ignore_errors=True))
        sub = d / "nodes" / "02-what" / "spec"
        sub.mkdir(parents=True)
        for s in stems:
            (sub / f"{s}.yaml").write_text("title: x\nversion: 0.1.0\n", encoding="utf-8")
            (sub / f"{s}.md").write_text("# x\n", encoding="utf-8")  # .md は無視される
        return d

    def test_from_dir_collects_stems_ok(self):
        d = self._mirror("brand-new-a", "brand-new-b")
        code, out, _ = self._run(["--from-dir", str(d)])
        self.assertEqual(code, cli.EXIT_OK)
        self.assertIn("収集", out)
        self.assertIn("brand-new-a", out)

    def test_from_dir_collision_fail_close(self):
        # 走査した stem の1つが既存コーパス id（target-p）と衝突 → fail-close。
        d = self._mirror("target-p", "brand-new-b")
        code, _, err = self._run(["--from-dir", str(d)])
        self.assertEqual(code, cli.EXIT_ERROR)
        self.assertIn("target-p", err)

    def test_from_dir_missing_dir_error(self):
        code, _, err = self._run(["--from-dir", "/no/such/dir/xyz"])
        self.assertEqual(code, cli.EXIT_NOT_FOUND)

    def test_from_dir_batch_dup_across_subdirs(self):
        # 本機能の目玉: 同一 slug が2つの parent サブツリーに現れると、
        # from-dir 収集（rglob）で重複が残り batch(xN) として fail-close する。
        d = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: __import__("shutil").rmtree(d, ignore_errors=True))
        for p in ("parent-a", "parent-b"):
            sub = d / p / "nodes" / "02-what" / "spec"
            sub.mkdir(parents=True)
            (sub / "dup.yaml").write_text("title: x\nversion: 0.1.0\n", encoding="utf-8")
        code, _, err = self._run(["--from-dir", str(d)])
        self.assertEqual(code, cli.EXIT_ERROR)
        self.assertIn("batch", err)
        self.assertIn("dup", err)

    def test_from_dir_plus_explicit_slug_merged(self):
        # from-dir 収集 slug と明示 slug 引数が併合されて一括判定される。
        d = self._mirror("fresh-from-dir")
        code, _, err = self._run(["target-p", "--from-dir", str(d)])  # 明示 = 既存 id
        self.assertEqual(code, cli.EXIT_ERROR)
        self.assertIn("target-p", err)

    # --- --update 宣言（既存ノード更新・issue #97・案A） ---
    def test_update_declared_existing_slug_exit_ok(self):
        # REGRESSION①: 宣言した更新 slug は既存 id と一致しても EXIT_OK。
        code, out, _ = self._run(["target-p", "--update", "target-p"])
        self.assertEqual(code, cli.EXIT_OK)
        self.assertIn("一意", out)
        self.assertIn("更新宣言", out)

    def test_undeclared_new_slug_corpus_collision_still_fails(self):
        # REGRESSION②: 非宣言の slug が既存 id と衝突なら EXIT_ERROR を維持。
        code, _, err = self._run(["target-p", "--update", "some-other-slug"])
        self.assertEqual(code, cli.EXIT_ERROR)
        self.assertIn("target-p", err)

    def test_batch_dup_fails_even_if_declared_update(self):
        # REGRESSION③: バッチ内重複は宣言有無に関わらず ROLLBACK。
        code, _, err = self._run(["target-p", "target-p", "--update", "target-p"])
        self.assertEqual(code, cli.EXIT_ERROR)
        self.assertIn("batch", err)

    def test_update_from_dir_slug_exit_ok(self):
        # from-dir で収集した既存 id を --update 宣言すれば通る（実運用フロー）。
        d = self._mirror("target-p", "brand-new-b")
        code, _, _ = self._run(["--from-dir", str(d), "--update", "target-p"])
        self.assertEqual(code, cli.EXIT_OK)

    # --- --update の typo ハードニング（コーパス非存在宣言への WARN・issue #103 Part B） ---
    def test_update_nonexistent_slug_warns_but_stays_ok(self):
        # 宣言 slug がコーパスに無い＝typo 疑い。fail-close は変えない（他に衝突が無ければ EXIT_OK）。
        code, _, err = self._run(["brand-new", "--update", "no-such-slug"])
        self.assertEqual(code, cli.EXIT_OK)
        self.assertIn("警告", err)
        self.assertIn("no-such-slug", err)

    def test_update_existing_slug_no_warn(self):
        # 宣言 slug がコーパスに実在すれば typo 警告は出ない。
        code, _, err = self._run(["target-p", "--update", "target-p"])
        self.assertEqual(code, cli.EXIT_OK)
        self.assertNotIn("警告", err)

    def test_update_mixed_existing_and_missing_warns_only_missing(self):
        # 複数 --update 宣言のうち実在しないものだけ WARN の対象になる。
        code, _, err = self._run(
            ["brand-new", "--update", "target-p", "--update", "no-such-slug"]
        )
        self.assertEqual(code, cli.EXIT_OK)
        self.assertIn("警告", err)
        self.assertIn("no-such-slug", err)
        # target-p は実在するので警告行には現れない（衝突メッセージにも登場しない＝EXIT_OK なので）。
        self.assertNotIn("target-p", err)


if __name__ == "__main__":
    unittest.main()
