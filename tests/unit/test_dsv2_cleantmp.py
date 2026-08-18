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


class TestGuardDocsMatchProtectedNames(unittest.TestCase):
    """K-11: 掃除ガードの説明が実装（``PROTECTED_DIRNAMES``）に追従していること。

    PR #314 で保護名が ``(_handoff, _karte)`` の 2 つになったのに、agent 定義は
    ``_handoff`` だけを挙げたままだった。掃除を実行するのはこの agent なので、
    **実装とドキュメントの不整合は後工程（reconciliation）の誤読に直結する**
    ——「``_karte`` は掃除対象だ」と読んで是正ループの状態を消しにいきかねない。
    保護名を増やしたら記述も増やす、を機械的に固定する。

    検査対象は ``.claude/agents/reconciliation.md`` **だけではない**（PR #319 R-06）:
    ``CLAUDE.md`` にも同型の追従漏れが残っていた。CLAUDE.md は
    ``inject-governance.sh`` が**毎ターン全エージェントに注入する統治規範の正本**なので、
    片方だけ直した状態は誤読源として最も影響が大きい。さらに ``dsv2/README.md``
    （フォーマット依存マップ）にも同じ抜けが3件目として残っていた（issue #315 OOS-1）。

    **round2（issue #315 N-01）で判明した構造欠陥**: 上記3件の是正後も、
    実装に最も近い ``dsv2/__init__.py``・``dsv2/cli.py``（module docstring・
    ``cmd_clean_tmp`` docstring の計3箇所）に同型ドリフトが残存していた（N-01）。
    これを当時の ``test_every_protected_name_appears_in_the_guard_description`` が
    検出できなかったのは、判定が**ファイル単位の blob** に対して保護名の存在を見る
    せいで、**同一ファイル内に正しい記述が1つあれば別の記述の欠落を検出できない**
    という構造欠陥があったため。

    **round2 是正の1周目（N-01 是正コミット）で追加した
    ``test_bare_handoff_reference_is_always_paired_with_karte`` は、なお同じ
    「ファイル単位 blob」判定を残したまま**（``test_every_protected_name_appears_in_the_guard_description``
    自体は変えず、別テストを追加しただけ）だったため、**N-02 として再指摘**された：
    ``_guard_blob`` が「``clean-tmp``/``保護名`` を含む全段落を連結してから ``assertIn``」する
    実装のままで、``dsv2/cli.py`` 内の独立した2つのガード段落（module docstring の bullet と
    ``cmd_clean_tmp`` docstring）間で保護名を**借用**できてしまっていた。加えて
    ``test_bare_handoff_reference_is_always_paired_with_karte`` のトリガーが
    ``` ``tmp/_handoff`` ``` という bare RST 参照形にしか反応しないため、是正後の実際の
    表記（``保護名（``_handoff``・``_karte``）`` 等・bare 形を使わない）では**一度も
    トリガーせず trivially に PASS していた**（issue #315 round2 レビュー申し送り）。

    **N-02 是正（本ラウンド）**: 上記2つの構造欠陥を、``_guard_paragraphs`` による
    **真の段落単位判定**へ統合して解消する——段落を連結せず、``clean-tmp``/``保護名`` に
    触れ**かつ**具体的な保護名（``_handoff``/``_karte`` のいずれか）を1つ以上挙げている
    段落だけを「ガード説明」とみなし、その段落**それぞれ単独**で
    ``cleantmp.PROTECTED_DIRNAMES`` の全メンバーを備えているかを検査する。
    「具体的な保護名を1つ以上挙げている」の条件を外すと、``_protected_component`` の
    docstring のように「保護名」という語だけを一般的に使う無関係な段落まで拾って
    誤検出する。「``clean-tmp``/``保護名`` に触れている」の条件を外すと、
    「戻り値のハンドオフ規約」（``tmp/_handoff/<key>.yaml`` 等）のような**掃除ガードとは
    無関係な ``_handoff`` 言及**まで拾って誤検出する（``.claude/agents/reconciliation.md``
    の「ハンドオフ」節が実例）。両条件を組み合わせることで、``test_bare_handoff_reference_
    is_always_paired_with_karte`` が意図していた「``_handoff`` に言及して ``_karte`` を
    欠く段落を検出する」を bare 形に限らず一般化しつつ、この新しい段落単位判定に統合した
    （重複テストを残さない）。

    対象文書も **静的な固定リストではなく、`clean-tmp`/`PROTECTED_DIRNAMES` に
    実際に触れているファイルを動的に絞り込んで**決める（``_discover_guard_docs``）。
    ``dsv2/*.py`` を候補にすべて数え上げつつ、無関係なモジュール（``dsv2/query.py`` 等）を
    「ガード説明が見つからない」で誤検出しないようにするため。
    """

    REPO_ROOT = Path(__file__).resolve().parents[2]
    # 保護名が 1 つしか書かれていない旧記述（是正前の実文言）。
    STALE_PHRASES = (
        "`_handoff` を含まず symlink でもない",
        "`_handoff` を含むパスを機械的に拒否する）",
        "`_handoff` を機械的に拒否する）",
    )

    @classmethod
    def _candidate_guard_docs(cls):
        # 規範の正本は Issue #387 で ``CLAUDE.md`` 単体から ``CLAUDE.md`` ＋
        # ``.claude/rules/*.md`` へ分割された。``CLAUDE.md`` だけを候補に残すと、
        # 掃除ガードの記述（現 ``.claude/rules/05-skills-agents.md``）が
        # ``_discover_guard_docs`` の絞り込みで**候補ごと消える**——テストは緑のまま
        # 検査対象が1件減る silent な fail-open になる。rules 全体を候補に入れ、
        # 実際にガードへ触れているファイルだけを動的に拾わせる（分割の仕方が
        # 将来また変わっても追従する）。
        return (
            cls.REPO_ROOT / ".claude" / "agents" / "reconciliation.md",
            cls.REPO_ROOT / "CLAUDE.md",
            *sorted((cls.REPO_ROOT / ".claude" / "rules").glob("*.md")),
            cls.REPO_ROOT / "dsv2" / "README.md",
            *sorted((cls.REPO_ROOT / "dsv2").glob("*.py")),
        )

    @classmethod
    def _discover_guard_docs(cls):
        """`clean-tmp`/`PROTECTED_DIRNAMES` に実際に触れている候補だけを対象にする。

        候補を無条件に GUARD_DOCS へ入れると、掃除ガードと無関係な ``dsv2/*.py``
        （``query.py`` 等）まで「ガード説明が見つからない」で fail してしまう
        （リポジトリ全体でこの2語に触れるファイルは7件のみ・issue #315 round2）。
        """
        docs = []
        for path in cls._candidate_guard_docs():
            text = path.read_text(encoding="utf-8")
            if "clean-tmp" in text or "PROTECTED_DIRNAMES" in text:
                docs.append(path)
        return tuple(docs)

    @classmethod
    def setUpClass(cls):
        cls.GUARD_DOCS = cls._discover_guard_docs()

    @staticmethod
    def _paragraphs(path: Path):
        """blank line 区切りの段落に分割する（word-wrap で同じ文が複数の物理行に
        分かれるケースを1つの検査単位にまとめるため）。"""
        text = path.read_text(encoding="utf-8")
        blocks = []
        current = []
        for line in text.splitlines():
            if line.strip():
                current.append(line)
            elif current:
                blocks.append(current)
                current = []
        if current:
            blocks.append(current)
        return ["\n".join(block) for block in blocks]

    @classmethod
    def _guard_paragraphs(cls, path: Path):
        """段落を連結せず、「ガード説明」段落だけを個別に返す（N-02 是正）。

        選定条件は次の**両方**を満たす段落：
          1. ``clean-tmp`` または ``保護名`` に触れている（掃除ガードの説明である）。
          2. ``cleantmp.PROTECTED_DIRNAMES`` のいずれか1つ以上を具体的に挙げている。

        条件1だけだと ``_protected_component`` の docstring のように「保護名」という
        語だけを一般的に使う無関係な段落（具体名を1つも挙げない）まで拾って誤検出する。
        条件2だけだと「戻り値のハンドオフ規約」の ``tmp/_handoff/<key>.yaml`` 言及のような
        掃除ガードとは無関係な ``_handoff`` 参照まで拾って誤検出する
        （``.claude/agents/reconciliation.md`` の「ハンドオフ」節が実例）。
        """
        return [
            para for para in cls._paragraphs(path)
            if ("clean-tmp" in para or "保護名" in para)
            and any(name in para for name in cleantmp.PROTECTED_DIRNAMES)
        ]

    def test_every_protected_name_appears_in_the_guard_description(self):
        """K-11 / N-02 是正: 各ガード段落は**単独で**全保護名を備えていること。

        段落を連結してから ``assertIn`` すると、同一ファイル内の別の段落から保護名を
        「借用」でき、片方の段落だけ欠落していても見逃す（N-02 の再指摘内容）。
        ここでは段落ごとに独立して不足を検査し、失敗時はどのファイルのどの段落かを
        メッセージに残す。

        ``test_bare_handoff_reference_is_always_paired_with_karte``（旧・issue #315
        round2 で追加）はこの段落単位判定に統合済み——``_handoff`` に言及して
        ``_karte`` を欠く段落は、ここで PROTECTED_DIRNAMES の不足として同じ経路で
        検出される（bare RST 形に限定されていた旧トリガーの一般化）。
        """
        self.assertTrue(self.GUARD_DOCS, "ガード対象文書が1件も見つからない")
        for doc in self.GUARD_DOCS:
            with self.subTest(doc=doc.name):
                guard_paragraphs = self._guard_paragraphs(doc)
                self.assertTrue(
                    guard_paragraphs, f"clean-tmp のガード説明が見つからない: {doc}"
                )
                for idx, para in enumerate(guard_paragraphs):
                    missing = [
                        name for name in cleantmp.PROTECTED_DIRNAMES
                        if name not in para
                    ]
                    with self.subTest(doc=doc.name, paragraph=idx):
                        self.assertEqual(
                            missing, [],
                            f"{doc} の段落 {idx} は保護名 {missing} を欠く: {para!r}",
                        )

    def test_guard_description_is_not_stale_on_a_single_name(self):
        """保護名が 1 つしか書かれていない旧記述が残っていないこと。"""
        for doc in self.GUARD_DOCS:
            text = doc.read_text(encoding="utf-8")
            for phrase in self.STALE_PHRASES:
                with self.subTest(doc=doc.name, phrase=phrase):
                    self.assertNotIn(phrase, text)


if __name__ == "__main__":
    unittest.main()
