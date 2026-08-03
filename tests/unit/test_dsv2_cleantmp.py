"""dsv2.cleantmp — tmp 著作ミラーの安全削除（ガード付き・reconciliation Step 3-3）。

境界値：``tmp/_handoff`` と ``tmp/_karte`` は拒否／``tmp/`` の外は拒否／階層違いは拒否／
正常系は削除される。``tmp/_karte``（是正ループの診断カルテ・Issue #307）は掃除で消えると
ループ状態そのものが失われるため、``_handoff`` と同じ保護名として固定する。
"""

import argparse
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from dsv2 import cleantmp
from dsv2 import cli as dsv2_cli
from dsv2.cli import EXIT_ERROR, EXIT_NOT_FOUND, EXIT_OK, main


def _make_repo(case) -> Path:
    """``tmp/sprint-1/parent-a``・``tmp/_handoff``・``tmp/_karte`` を持つ疑似リポジトリを作る。"""
    root = Path(tempfile.mkdtemp(prefix="cleantmp-")).resolve()
    case.addCleanup(lambda: __import__("shutil").rmtree(root, ignore_errors=True))
    target = root / "tmp" / "sprint-1" / "parent-a" / "nodes" / "02-spec" / "spec"
    target.mkdir(parents=True)
    (target / "some-slug.md").write_text("# SPEC\n", encoding="utf-8")
    (target / "some-slug.yaml").write_text('title: "x"\n', encoding="utf-8")
    handoff = root / "tmp" / "_handoff"
    handoff.mkdir(parents=True)
    (handoff / "spec-author--parent-a.yaml").write_text("agent: spec-author\n", encoding="utf-8")
    karte = root / "tmp" / "_karte"
    karte.mkdir(parents=True)
    (karte / "issue-307.md").write_text("# Karte: issue-307\n", encoding="utf-8")
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

    def test_rejects_karte_dir(self):
        """診断カルテ置き場は掃除対象外（Issue #307・ループ状態が失われる）。"""
        with self.assertRaises(cleantmp.CleanTmpError) as ctx:
            cleantmp.plan_clean(self.root / "tmp/_karte", self.root)
        self.assertIn("_karte", str(ctx.exception))
        self.assertTrue((self.root / "tmp/_karte/issue-307.md").is_file())

    def test_rejects_path_under_karte(self):
        """``tmp/_karte/<sub>`` はちょうど2階層なので階層ガードでは弾けない。
        保護名ガードが効いていることを固定する（Issue #307）。"""
        (self.root / "tmp/_karte/sub").mkdir()
        with self.assertRaises(cleantmp.CleanTmpError) as ctx:
            cleantmp.plan_clean(self.root / "tmp/_karte/sub", self.root)
        self.assertIn("_karte", str(ctx.exception))
        self.assertTrue((self.root / "tmp/_karte/sub").is_dir())

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

    def test_rejects_tmp_root_itself_symlink(self):
        """<repo>/tmp 自体が symlink の場合、is_dir() が追跡して真になり得るため、
        symlink であること自体を明示的に拒否する（Codex 指摘・issue #276 round-3）。
        symlink 先（repo 外）には一切触れないことも確認する。"""
        root = Path(tempfile.mkdtemp(prefix="cleantmp-tmproot-")).resolve()
        self.addCleanup(lambda: shutil.rmtree(root, ignore_errors=True))
        outside = Path(tempfile.mkdtemp(prefix="cleantmp-outside-"))
        self.addCleanup(lambda: shutil.rmtree(outside, ignore_errors=True))
        (outside / "sprint-1" / "parent-a").mkdir(parents=True)
        (outside / "sentinel.txt").write_text("do not delete me\n", encoding="utf-8")

        tmp_link = root / "tmp"
        try:
            tmp_link.symlink_to(outside)
        except (OSError, NotImplementedError):  # pragma: no cover - symlink 不可環境
            self.skipTest("symlink を作れない環境")

        with self.assertRaises(cleantmp.CleanTmpError) as ctx:
            cleantmp.plan_clean(root / "tmp/sprint-1/parent-a", root)
        self.assertIn("symlink", str(ctx.exception))
        # symlink 先の repo 外ディレクトリは一切変更されていないこと。
        self.assertTrue(outside.exists())
        self.assertTrue((outside / "sentinel.txt").is_file())
        self.assertTrue((outside / "sprint-1" / "parent-a").is_dir())


class TestApply(unittest.TestCase):
    def setUp(self):
        self.root = _make_repo(self)

    def test_apply_removes_only_target(self):
        plan = cleantmp.plan_clean(self.root / "tmp/sprint-1/parent-a", self.root)
        cleantmp.apply_clean(plan)
        self.assertFalse((self.root / "tmp/sprint-1/parent-a").exists())
        self.assertTrue((self.root / "tmp/_handoff/spec-author--parent-a.yaml").is_file())
        self.assertTrue((self.root / "tmp/_karte/issue-307.md").is_file())
        self.assertTrue((self.root / "tmp/sprint-1").is_dir())

    def test_apply_rejects_symlink_swapped_after_plan(self):
        """TOCTOU: plan_clean 後・apply_clean 前に対象が symlink へ差し替わった場合、
        apply_clean は削除直前の再検査（_reverify_before_delete）で検知して拒否する。"""
        plan = cleantmp.plan_clean(self.root / "tmp/sprint-1/parent-a", self.root)
        outside = Path(tempfile.mkdtemp(prefix="cleantmp-outside-"))
        self.addCleanup(lambda: shutil.rmtree(outside, ignore_errors=True))
        (outside / "sentinel.txt").write_text("do not delete me\n", encoding="utf-8")

        shutil.rmtree(plan.target)  # 元ディレクトリを撤去してから symlink に差し替える
        try:
            plan.target.symlink_to(outside)
        except (OSError, NotImplementedError):  # pragma: no cover - symlink 不可環境
            self.skipTest("symlink を作れない環境")

        with self.assertRaises(cleantmp.CleanTmpError) as ctx:
            cleantmp.apply_clean(plan)
        self.assertIn("symlink", str(ctx.exception))
        self.assertTrue(outside.exists())
        self.assertTrue((outside / "sentinel.txt").is_file())

    def test_apply_rejects_target_moved_outside_after_plan(self):
        """TOCTOU: plan 作成後に対象パスの実体（親ディレクトリ経由）が tmp/ の外を
        指すよう差し替わった場合も、apply_clean は再検査で拒否する。"""
        plan = cleantmp.plan_clean(self.root / "tmp/sprint-1/parent-a", self.root)
        outside = Path(tempfile.mkdtemp(prefix="cleantmp-outside-"))
        self.addCleanup(lambda: shutil.rmtree(outside, ignore_errors=True))

        # sprint-1 ディレクトリごと symlink 差し替え（中間コンポーネントの TOCTOU）。
        sprint_dir = self.root / "tmp/sprint-1"
        shutil.rmtree(sprint_dir)
        try:
            sprint_dir.symlink_to(outside)
        except (OSError, NotImplementedError):  # pragma: no cover - symlink 不可環境
            self.skipTest("symlink を作れない環境")

        with self.assertRaises(cleantmp.CleanTmpError):
            cleantmp.apply_clean(plan)
        self.assertTrue(outside.exists())


class TestCli(unittest.TestCase):
    def setUp(self):
        self.root = _make_repo(self)

    def _run(self, path, apply_=False):
        """``--repo-root`` は公開 CLI フラグとして存在しない（issue #276 round-2）。
        テストは argparse を経由せず、``cmd_clean_tmp`` を内部専用の ``repo_root``
        属性つき Namespace で直接呼び、同じガード動作を検証する。"""
        ns = argparse.Namespace(path=str(path), apply=apply_, repo_root=str(self.root))
        return dsv2_cli.cmd_clean_tmp(ns)

    def test_dry_run_keeps_files(self):
        self.assertEqual(self._run(self.root / "tmp/sprint-1/parent-a"), EXIT_OK)
        self.assertTrue((self.root / "tmp/sprint-1/parent-a").is_dir())

    def test_apply_deletes(self):
        self.assertEqual(self._run(self.root / "tmp/sprint-1/parent-a", apply_=True), EXIT_OK)
        self.assertFalse((self.root / "tmp/sprint-1/parent-a").exists())

    def test_handoff_is_rejected_with_exit_error(self):
        self.assertEqual(self._run(self.root / "tmp/_handoff", apply_=True), EXIT_ERROR)
        self.assertTrue((self.root / "tmp/_handoff").is_dir())

    def test_karte_is_rejected_with_exit_error(self):
        """``dsv2 clean-tmp --apply`` が ``tmp/_karte/`` を削除しない（Issue #307 受入基準）。"""
        self.assertEqual(self._run(self.root / "tmp/_karte", apply_=True), EXIT_ERROR)
        self.assertTrue((self.root / "tmp/_karte/issue-307.md").is_file())

    def test_outside_tmp_is_rejected_with_exit_error(self):
        self.assertEqual(self._run(self.root / "doc-system-v2/nodes", apply_=True), EXIT_ERROR)
        self.assertTrue((self.root / "doc-system-v2/nodes").is_dir())

    def test_missing_target_exit_not_found(self):
        self.assertEqual(self._run(self.root / "tmp/sprint-1/nope", apply_=True), EXIT_NOT_FOUND)

    def test_repo_root_flag_not_on_public_cli_surface(self):
        """``--repo-root`` は argparse に登録されていない（公開フラグとして提供しない）。
        main() 経由で渡すと argparse の用法エラー（SystemExit(2)）になることを確認する。"""
        with self.assertRaises(SystemExit) as ctx:
            main(["clean-tmp", str(self.root / "tmp/sprint-1/parent-a"),
                  "--repo-root", str(self.root)])
        self.assertEqual(ctx.exception.code, 2)

    def test_apply_clean_error_at_delete_time_returns_exit_error(self):
        """``apply_clean`` が（``_reverify_before_delete`` の TOCTOU 再検査等で）
        ``CleanTmpError`` を送出した場合も ``cmd_clean_tmp`` は uncaught にせず
        EXIT_ERROR で fail-close する（Codex 指摘・issue #276 round-3）。
        plan_clean と apply_clean の間で実際に symlink を差し替えるのは TestApply 側で
        別途カバー済みのため、ここは cmd_clean_tmp の例外ハンドリングそのものを
        mock で単体検証する。"""
        with mock.patch.object(
            dsv2_cli.cleantmp, "apply_clean",
            side_effect=cleantmp.CleanTmpError("boom（TOCTOU 疑い）"),
        ):
            result = self._run(self.root / "tmp/sprint-1/parent-a", apply_=True)
        self.assertEqual(result, EXIT_ERROR)
        # apply_clean をモックで差し替えている＝実削除は起きていないはず。
        self.assertTrue((self.root / "tmp/sprint-1/parent-a").is_dir())

    def test_main_full_argparse_dry_run_and_apply(self):
        """round-1 修正で ``--repo-root`` フラグを撤去して以降、``TestCli`` の他テストは
        すべて ``cmd_clean_tmp`` を argparse.Namespace 手組みで直接呼んでおり、
        ``main()``/argparse による実際の ``path`` 位置引数・``--apply`` フラグの解析を
        既定 repo root（モジュール直の ``_REPO_ROOT``）経由で通す成功系テストが無かった
        （Codex 指摘・issue #276 round-3）。``_REPO_ROOT`` をテスト fixture root に
        差し替えて main() をフル経由で dry-run → --apply の順に検証する。"""
        target = self.root / "tmp/sprint-1/parent-a"
        with mock.patch.object(dsv2_cli, "_REPO_ROOT", self.root):
            self.assertEqual(main(["clean-tmp", str(target)]), EXIT_OK)
            self.assertTrue(target.is_dir())  # dry-run では削除されない

            self.assertEqual(main(["clean-tmp", str(target), "--apply"]), EXIT_OK)
            self.assertFalse(target.exists())  # --apply で実削除される


class TestReconciliationDocMatchesProtectedNames(unittest.TestCase):
    """K-11: `.claude/agents/reconciliation.md` のガード説明が実装に追従していること。

    PR #314 で保護名が ``(_handoff, _karte)`` の 2 つになったのに、agent 定義は
    ``_handoff`` だけを挙げたままだった。掃除を実行するのはこの agent なので、
    **実装とドキュメントの不整合は後工程（reconciliation）の誤読に直結する**
    ——「``_karte`` は掃除対象だ」と読んで是正ループの状態を消しにいきかねない。
    保護名を増やしたら記述も増やす、を機械的に固定する。
    """

    AGENT_DOC = (
        Path(__file__).resolve().parents[2] / ".claude" / "agents" / "reconciliation.md"
    )

    def test_every_protected_name_appears_in_the_guard_description(self):
        text = self.AGENT_DOC.read_text(encoding="utf-8")
        guard_lines = [
            line for line in text.splitlines()
            if "clean-tmp" in line or "保護名" in line
        ]
        self.assertTrue(guard_lines, "clean-tmp のガード説明が見つからない")
        blob = "\n".join(guard_lines)
        for name in cleantmp.PROTECTED_DIRNAMES:
            with self.subTest(protected=name):
                self.assertIn(name, blob)

    def test_guard_description_is_not_stale_on_a_single_name(self):
        """保護名が 1 つしか書かれていない旧記述が残っていないこと。"""
        text = self.AGENT_DOC.read_text(encoding="utf-8")
        self.assertNotIn("`_handoff` を含まず symlink でもない", text)
        self.assertNotIn("`_handoff` を含むパスを機械的に拒否する）", text)


if __name__ == "__main__":
    unittest.main()
