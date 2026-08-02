"""karte — 是正ループの診断カルテ CLI（Issue #307）。

受入基準に対応するテスト:
  * 5 verb（＋実測取り込みの ``close-attempt``）が動作する。
  * ``root_cause`` 一致＋``targets`` 交差の 3 件目の Attempt が拒否され、反復された
    ``root_cause`` / ``targets`` を名指しした転換指令が stdout に返る。
  * ラベル（``root_cause``/``change_kind``）を変えても実測 touched-set が同一なら拒否される。
  * 毎回異なる ``root_cause``/``targets`` なら回数無制限で ``append`` が通る（回数上限なし）。
  * ``ingest-review`` → ``append`` → ``status`` で finding ID 単位に指摘・診断・処置結果が引ける。
  * 未解消 finding への ID 再発番（同一指摘への新 ID 付与）が検出される。
  * ``status`` が「実害あり残存」「全件実害なし」「同一 finding_id が 3 ラウンド連続未解消」を判別する。
  * repo-root 外・``..`` traversal・symlink 経由のパスを fail-close で拒否する。
"""

import argparse
import contextlib
import io
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from karte import cli, model, paths, similarity, touched


def _make_repo(case) -> Path:
    root = Path(tempfile.mkdtemp(prefix="karte-")).resolve()
    case.addCleanup(lambda: shutil.rmtree(root, ignore_errors=True))
    (root / "tmp").mkdir()
    return root


def _report(*findings) -> str:
    """``### <title>`` ブロック列のレビューレポート本文を組み立てる。"""
    blocks = []
    for title, fields in findings:
        lines = [f"### {title}"]
        lines += [f"{key}: {value}" for key, value in fields.items()]
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks) + "\n"


class KarteTestCase(unittest.TestCase):
    """``cmd_*`` を ``argparse.Namespace`` 直呼びで検証する共通土台。

    ``repo_root`` は公開 CLI フラグではない内部専用パラメータ（``dsv2`` の
    ``cmd_clean_tmp`` と同じ設計）なので、テストは Namespace を手組みして渡す。
    """

    issue = 307

    def setUp(self):
        self.root = _make_repo(self)

    # --- 呼び出しヘルパ ---
    def _ns(self, **kwargs):
        base = {"issue": str(self.issue), "repo_root": str(self.root)}
        base.update(kwargs)
        return argparse.Namespace(**base)

    def _run(self, func, **kwargs):
        buffer = io.StringIO()
        errors = io.StringIO()
        with contextlib.redirect_stdout(buffer), contextlib.redirect_stderr(errors):
            code = func(self._ns(**kwargs))
        return code, buffer.getvalue(), errors.getvalue()

    def _write_report(self, name, text) -> str:
        path = self.root / "tmp" / name
        path.write_text(text, encoding="utf-8")
        return str(path)

    def _ingest(self, round_no, *findings):
        source = self._write_report(f"review-{round_no}.md", _report(*findings))
        return self._run(cli.cmd_ingest_review, round=str(round_no), source=source)

    def _append(self, **kwargs):
        params = {
            "round": None,
            "finding_ids": ["F-307-01"],
            "root_cause": "some-cause",
            "change_kind": "logic",
            "targets": ["a/b.py::f"],
            "diagnosis": "",
        }
        params.update(kwargs)
        return self._run(cli.cmd_append, **params)

    def _close(self, attempt, diff_text, outcome="partial", note=""):
        diff_path = self._write_report(f"diff-{attempt}.patch", diff_text)
        return self._run(
            cli.cmd_close_attempt,
            attempt=str(attempt),
            outcome=outcome,
            finding_ids=None,
            base="HEAD",
            diff_file=diff_path,
            note=note,
        )

    def _karte(self):
        path = paths.karte_path(self.issue, self.root)
        return model.parse(path.read_text(encoding="utf-8"))


HARMFUL = {
    "harm": "real",
    "harm_detail": "必須属性が消えて入力検証が素通りする",
    "locus": "a/b.py::build_attrs",
    "summary": "build_attrs が既存 attrs を破棄している",
}
COSMETIC = {
    "harm": "none",
    "harm_detail": "表記ゆれのみで挙動に影響しない",
    "locus": "docs/readme.md",
    "summary": "見出しの用語がゆれている",
}


# --- ingest-review -----------------------------------------------------------


class TestIngestReview(KarteTestCase):
    def test_creates_karte_and_allocates_ids(self):
        code, out, _err = self._ingest(1, ("new", HARMFUL), ("new", COSMETIC))
        self.assertEqual(code, cli.EXIT_OK)
        self.assertIn("F-307-01", out)
        self.assertIn("F-307-02", out)
        karte = self._karte()
        self.assertEqual([f.id for f in karte.findings], ["F-307-01", "F-307-02"])
        self.assertEqual(karte.finding("F-307-01").rounds, [1])
        self.assertEqual(karte.finding("F-307-01").harm, "real")

    def test_active_pointer_written_without_agent_id(self):
        self._ingest(1, ("new", HARMFUL))
        active = json.loads((self.root / "tmp/_karte/active.json").read_text(encoding="utf-8"))
        self.assertEqual(active, {"issue": 307, "round": 1})

    def test_missing_harm_is_rejected(self):
        broken = dict(HARMFUL)
        del broken["harm"]
        code, _out, err = self._ingest(1, ("new", broken))
        self.assertEqual(code, cli.EXIT_ERROR)
        self.assertIn("harm", err)
        self.assertFalse((self.root / "tmp/_karte/issue-307.md").exists())

    def test_duplicate_id_in_report_is_rejected(self):
        self._ingest(1, ("new", HARMFUL))
        other = dict(COSMETIC)
        code, _out, err = self._ingest(2, ("F-307-01", HARMFUL), ("F-307-01", other))
        self.assertEqual(code, cli.EXIT_ERROR)
        self.assertIn("重複", err)

    def test_unknown_id_is_rejected(self):
        self._ingest(1, ("new", HARMFUL))
        code, _out, err = self._ingest(2, ("F-307-09", COSMETIC))
        self.assertEqual(code, cli.EXIT_ERROR)
        self.assertIn("未知の finding ID", err)

    def test_reissued_id_for_same_finding_is_detected(self):
        """未解消の指摘に新しい ID を振り直したら検出する（受入基準）。"""
        self._ingest(1, ("new", HARMFUL))
        reworded = dict(HARMFUL)
        reworded["summary"] = "build_attrs が既存の attrs を破棄している（再掲）"
        code, _out, err = self._ingest(2, ("new", reworded))
        self.assertEqual(code, cli.EXIT_ERROR)
        self.assertIn("ID 再発番", err)
        self.assertIn("F-307-01", err)
        self.assertEqual(len(self._karte().findings), 1)  # 何も書かれていない

    def test_not_reraised_finding_becomes_resolved(self):
        self._ingest(1, ("new", HARMFUL), ("new", COSMETIC))
        code, _out, _err = self._ingest(2, ("F-307-01", HARMFUL))
        self.assertEqual(code, cli.EXIT_OK)
        karte = self._karte()
        self.assertEqual(karte.finding("F-307-02").status, "resolved")
        self.assertEqual(karte.finding("F-307-02").resolved_round, 2)
        self.assertEqual(karte.finding("F-307-01").rounds, [1, 2])

    def test_round_must_be_monotonic(self):
        self._ingest(2, ("new", HARMFUL))
        code, _out, err = self._ingest(2, ("F-307-01", HARMFUL))
        self.assertEqual(code, cli.EXIT_ERROR)
        self.assertIn("単調増加", err)

    def test_report_without_blocks_is_rejected(self):
        source = self._write_report("empty.md", "# レビュー結果\n\n特になし\n")
        code, _out, err = self._run(cli.cmd_ingest_review, round="1", source=source)
        self.assertEqual(code, cli.EXIT_ERROR)
        self.assertIn("finding ブロック", err)


# --- append（類似判定） -------------------------------------------------------


class TestAppendSimilarity(KarteTestCase):
    def setUp(self):
        super().setUp()
        self._ingest(1, ("new", HARMFUL))

    def test_third_similar_attempt_is_rejected_with_directive(self):
        """root_cause 一致＋targets 交差の 3 件目が拒否され、転換指令が stdout に返る。"""
        for targets in (["a/b.py::build_attrs"], ["a/b.py::build_attrs", "a/b.py::render"]):
            code, _out, _err = self._append(root_cause="attrs-overwrite", targets=targets)
            self.assertEqual(code, cli.EXIT_OK)

        code, out, _err = self._append(
            root_cause="attrs-overwrite", change_kind="test", targets=["a/b.py::build_attrs"]
        )
        self.assertEqual(code, cli.EXIT_SATURATED)
        self.assertIn("DIRECTIVE", out)
        self.assertIn("attrs-overwrite", out)          # 反復された root_cause を名指し
        self.assertIn("a/b.py::build_attrs", out)      # 反復された targets を名指し
        self.assertIn("F-307-01", out)
        self.assertEqual(len(self._karte().attempts), 2)  # 書き込まれていない

    def test_distinct_approaches_are_never_capped(self):
        """毎回異なる root_cause / targets なら回数無制限で通る（ラウンド上限なし）。"""
        for index in range(1, 8):
            code, _out, err = self._append(
                root_cause=f"cause-{index}", targets=[f"pkg/mod{index}.py::fn{index}"]
            )
            self.assertEqual(code, cli.EXIT_OK, msg=f"{index} 回目で拒否された: {err}")
        self.assertEqual(len(self._karte().attempts), 7)

    def test_same_root_cause_but_disjoint_targets_and_kind_is_allowed(self):
        self._append(root_cause="shared", change_kind="logic", targets=["x/a.py::f"])
        code, _out, _err = self._append(
            root_cause="shared", change_kind="interface", targets=["y/b.py::g"]
        )
        self.assertEqual(code, cli.EXIT_OK)

    def test_relabeled_attempt_with_same_touched_set_is_rejected(self):
        """ラベルを変えても実測 touched-set が同一なら拒否される（受入基準）。

        実測値は修正後に ``close-attempt`` で取り込まれ、**次の append の判定**で効く
        （診断は修正の前に走るため、append 時点では新規 Attempt に差分が存在しない）。
        宣言信号は root_cause / change_kind をすべて変えているので発火しない
        ＝拒否は実測信号によるものであることを確認する。
        """
        diff = (
            "--- a/pkg/forms.py\n"
            "+++ b/pkg/forms.py\n"
            "@@ -1,2 +1,2 @@ def build_attrs(self):\n"
            "-    attrs = {}\n"
            "+    attrs = dict(base)\n"
        )
        self._append(root_cause="cause-one", change_kind="logic", targets=["pkg/forms.py::build_attrs"])
        self._close(1, diff)
        self._append(root_cause="cause-two", change_kind="data-structure",
                     targets=["pkg/forms.py::build_attrs"])
        self._close(2, diff)

        code, out, _err = self._append(
            root_cause="cause-three", change_kind="interface",
            targets=["pkg/forms.py::build_attrs"],
        )
        self.assertEqual(code, cli.EXIT_SATURATED)
        self.assertIn("実測 touched-set が一致", out)
        self.assertIn("pkg/forms.py::build_attrs", out)
        self.assertEqual(len(self._karte().attempts), 2)

    def test_unknown_finding_id_is_rejected(self):
        code, _out, err = self._run(
            cli.cmd_append, round=None, finding_ids=["F-307-42"], root_cause="x",
            change_kind="logic", targets=["a/b.py::f"], diagnosis="",
        )
        self.assertEqual(code, cli.EXIT_ERROR)
        self.assertIn("未知の finding ID", err)

    def test_invalid_root_cause_slug_is_rejected(self):
        code, _out, err = self._append(root_cause="Attrs Overwrite")
        self.assertEqual(code, cli.EXIT_ERROR)
        self.assertIn("slug", err)

    def test_resolved_findings_do_not_gate(self):
        """解消済み finding に対する過去試行は類似グループに数えない（未解消のみが対象）。"""
        self._append(root_cause="same", targets=["a/b.py::f"])
        self._append(root_cause="same", targets=["a/b.py::f"])
        self._ingest(2, ("new", COSMETIC))  # F-307-01 は再掲されず解消、F-307-02 が新規
        code, _out, _err = self._append(
            finding_ids=["F-307-02"], root_cause="same", targets=["a/b.py::f"]
        )
        self.assertEqual(code, cli.EXIT_OK)


# --- close-attempt -----------------------------------------------------------


class TestCloseAttempt(KarteTestCase):
    def setUp(self):
        super().setUp()
        self._ingest(1, ("new", HARMFUL))
        self._append(root_cause="cause-one", targets=["pkg/forms.py::build_attrs"])

    def test_records_measured_touched_set_as_result_block(self):
        diff = (
            "diff --git a/pkg/forms.py b/pkg/forms.py\n"
            "--- a/pkg/forms.py\n"
            "+++ b/pkg/forms.py\n"
            "@@ -3,1 +3,2 @@ def build_attrs(self):\n"
            "+    attrs.update(extra)\n"
        )
        code, out, _err = self._close(1, diff, outcome="fixed", note="属性の合成に変更")
        self.assertEqual(code, cli.EXIT_OK)
        self.assertIn("pkg/forms.py::build_attrs", out)
        karte = self._karte()
        self.assertEqual(karte.touched_of(1), ["pkg/forms.py", "pkg/forms.py::build_attrs"])
        self.assertEqual(karte.results_for(1)[0].outcome, "fixed")
        # Attempt ブロックは書き換えられていない（追記のみ）。
        self.assertEqual(karte.attempt(1).root_cause, "cause-one")

    def test_double_close_is_rejected(self):
        diff = "--- a/x.py\n+++ b/x.py\n@@ -1 +1 @@\n-a\n+b\n"
        self._close(1, diff)
        code, _out, err = self._close(1, diff)
        self.assertEqual(code, cli.EXIT_ERROR)
        self.assertIn("既に Result がある", err)

    def test_missing_attempt_is_rejected(self):
        code, _out, err = self._close(9, "--- a/x.py\n+++ b/x.py\n@@ -1 +1 @@\n-a\n+b\n")
        self.assertEqual(code, cli.EXIT_ERROR)
        self.assertIn("Attempt 9", err)


# --- check / status ----------------------------------------------------------


class TestCheck(KarteTestCase):
    def setUp(self):
        super().setUp()
        self._ingest(1, ("new", HARMFUL), ("new", COSMETIC))

    def test_missing_attempt_for_round(self):
        code, _out, err = self._run(cli.cmd_check, round="1")
        self.assertEqual(code, cli.EXIT_ERROR)
        self.assertIn("Attempt が 1 件も無い", err)

    def test_partial_coverage_is_flagged(self):
        self._append(finding_ids=["F-307-01"], root_cause="c1", targets=["a/b.py::f"])
        code, _out, err = self._run(cli.cmd_check, round="1")
        self.assertEqual(code, cli.EXIT_ERROR)
        self.assertIn("F-307-02", err)

    def test_full_coverage_passes(self):
        self._append(
            finding_ids=["F-307-01", "F-307-02"], root_cause="c1", targets=["a/b.py::f"]
        )
        code, out, _err = self._run(cli.cmd_check, round="1")
        self.assertEqual(code, cli.EXIT_OK)
        self.assertIn("網羅", out)


class TestStatus(KarteTestCase):
    def test_harmful_open(self):
        self._ingest(1, ("new", HARMFUL), ("new", COSMETIC))
        code, out, _err = self._run(cli.cmd_status, json=False)
        self.assertEqual(code, cli.EXIT_OK)
        self.assertIn("harmful-open", out)

    def test_no_harm_only(self):
        self._ingest(1, ("new", COSMETIC))
        code, out, _err = self._run(cli.cmd_status, json=False)
        self.assertEqual(code, cli.EXIT_OK)
        self.assertIn("no-harm-only", out)

    def test_clean(self):
        self._ingest(1, ("new", HARMFUL))
        self._ingest(2, ("new", COSMETIC))
        self._ingest(3, ("F-307-02", COSMETIC))
        self._ingest(4, ("new", HARMFUL))  # 一旦全解消してから別件を挙げる
        karte = self._karte()
        self.assertEqual(karte.finding("F-307-02").status, "resolved")

    def test_stalled_when_same_finding_open_for_three_rounds(self):
        """同一 finding_id が 3 ラウンド連続未解消なら無進捗と判定する（受入基準）。"""
        self._ingest(1, ("new", HARMFUL))
        code, out, _err = self._run(cli.cmd_status, json=True)
        self.assertNotIn("F-307-01", json.loads(out)["stalled_findings"])

        self._ingest(2, ("F-307-01", HARMFUL))
        self._ingest(3, ("F-307-01", HARMFUL))
        code, out, _err = self._run(cli.cmd_status, json=True)
        payload = json.loads(out)
        self.assertEqual(payload["stalled_findings"], ["F-307-01"])
        self.assertTrue(payload["escalate"])

    def test_json_traces_finding_to_diagnosis_and_result(self):
        """finding ID 単位で指摘・診断・処置結果が引ける（ingest → append → status）。"""
        self._ingest(1, ("new", HARMFUL))
        self._append(root_cause="attrs-overwrite", targets=["pkg/forms.py::build_attrs"],
                     diagnosis="既存 attrs を作り直している")
        self._close(1, "--- a/pkg/forms.py\n+++ b/pkg/forms.py\n@@ -1 +1 @@ def build_attrs(self):\n-x\n+y\n",
                    outcome="partial", note="required は直ったが aria が残る")
        _code, out, _err = self._run(cli.cmd_status, json=True)
        finding = json.loads(out)["findings"][0]
        self.assertEqual(finding["id"], "F-307-01")
        self.assertEqual(finding["harm"], "real")
        self.assertEqual(finding["attempts"][0]["root_cause"], "attrs-overwrite")
        self.assertEqual(finding["attempts"][0]["results"][0]["outcome"], "partial")
        self.assertIn("pkg/forms.py::build_attrs", finding["attempts"][0]["results"][0]["touched"])


class TestRender(KarteTestCase):
    def test_render_lists_prior_attempts_and_open_findings(self):
        self._ingest(1, ("new", HARMFUL))
        self._append(root_cause="attrs-overwrite", targets=["pkg/forms.py::build_attrs"])
        code, out, _err = self._run(cli.cmd_render)
        self.assertEqual(code, cli.EXIT_OK)
        self.assertIn("Prior attempts（DO NOT repeat these）", out)
        self.assertIn("Attempt 1", out)
        self.assertIn("F-307-01", out)

    def test_render_emits_directive_when_group_saturated(self):
        self._ingest(1, ("new", HARMFUL))
        self._append(root_cause="attrs-overwrite", targets=["pkg/forms.py::build_attrs"])
        self._append(root_cause="attrs-overwrite", targets=["pkg/forms.py::build_attrs"])
        _code, out, _err = self._run(cli.cmd_render)
        self.assertIn("類似グループ飽和", out)
        self.assertIn("DIRECTIVE", out)

    def test_render_without_karte_is_not_found(self):
        code = cli.main(["render", "--issue", "999"])
        self.assertEqual(code, cli.EXIT_NOT_FOUND)


# --- パスガード ---------------------------------------------------------------


class TestPathGuards(KarteTestCase):
    def test_issue_number_must_be_plain_integer(self):
        for bad in ("../../etc", "0", "-1", "1 2", "01", ""):
            with self.assertRaises(paths.KartePathError):
                paths.validate_issue(bad)

    def test_parent_traversal_is_rejected(self):
        with self.assertRaises(paths.KartePathError) as ctx:
            paths.resolve_within_repo(self.root / "tmp" / ".." / ".." / "etc", self.root)
        self.assertIn("traversal", str(ctx.exception))

    def test_outside_repo_root_is_rejected(self):
        outside = Path(tempfile.mkdtemp(prefix="karte-outside-")).resolve()
        self.addCleanup(lambda: shutil.rmtree(outside, ignore_errors=True))
        with self.assertRaises(paths.KartePathError) as ctx:
            paths.resolve_within_repo(outside / "secret.md", self.root)
        self.assertIn("repo-root の外", str(ctx.exception))

    def test_symlinked_component_is_rejected(self):
        outside = Path(tempfile.mkdtemp(prefix="karte-outside-")).resolve()
        self.addCleanup(lambda: shutil.rmtree(outside, ignore_errors=True))
        (outside / "secret.md").write_text("secret\n", encoding="utf-8")
        link = self.root / "tmp" / "link"
        try:
            link.symlink_to(outside)
        except (OSError, NotImplementedError):  # pragma: no cover - symlink 不可環境
            self.skipTest("symlink を作れない環境")
        with self.assertRaises(paths.KartePathError) as ctx:
            paths.resolve_within_repo(link / "secret.md", self.root)
        self.assertIn("symlink", str(ctx.exception))

    def test_karte_dir_symlink_is_rejected(self):
        outside = Path(tempfile.mkdtemp(prefix="karte-outside-")).resolve()
        self.addCleanup(lambda: shutil.rmtree(outside, ignore_errors=True))
        link = self.root / "tmp" / "_karte"
        try:
            link.symlink_to(outside)
        except (OSError, NotImplementedError):  # pragma: no cover - symlink 不可環境
            self.skipTest("symlink を作れない環境")
        with self.assertRaises(paths.KartePathError) as ctx:
            paths.karte_path(307, self.root, create_dir=True)
        self.assertIn("symlink", str(ctx.exception))
        self.assertEqual(list(outside.iterdir()), [])

    def test_tmp_root_symlink_is_rejected(self):
        root = Path(tempfile.mkdtemp(prefix="karte-bare-")).resolve()
        self.addCleanup(lambda: shutil.rmtree(root, ignore_errors=True))
        outside = Path(tempfile.mkdtemp(prefix="karte-outside-")).resolve()
        self.addCleanup(lambda: shutil.rmtree(outside, ignore_errors=True))
        try:
            (root / "tmp").symlink_to(outside)
        except (OSError, NotImplementedError):  # pragma: no cover - symlink 不可環境
            self.skipTest("symlink を作れない環境")
        with self.assertRaises(paths.KartePathError) as ctx:
            paths.karte_dir(root, create=True)
        self.assertIn("symlink", str(ctx.exception))

    def test_ingest_rejects_report_outside_repo(self):
        outside = Path(tempfile.mkdtemp(prefix="karte-outside-")).resolve()
        self.addCleanup(lambda: shutil.rmtree(outside, ignore_errors=True))
        source = outside / "review.md"
        source.write_text(_report(("new", HARMFUL)), encoding="utf-8")
        code, _out, err = self._run(cli.cmd_ingest_review, round="1", source=str(source))
        self.assertEqual(code, cli.EXIT_ERROR)
        self.assertIn("repo-root の外", err)

    def test_repo_root_flag_not_on_public_cli_surface(self):
        with self.assertRaises(SystemExit) as ctx:
            cli.main(["status", "--issue", "307", "--repo-root", str(self.root)])
        self.assertEqual(ctx.exception.code, 2)


# --- 純関数（書式・類似・差分） ------------------------------------------------


class TestModel(unittest.TestCase):
    def test_roundtrip(self):
        karte = model.new_karte(307)
        karte.findings.append(
            model.Finding(id="F-307-01", harm="real", harm_detail="壊れる",
                          locus="a.py::f", summary="要約", rounds=[1, 2])
        )
        karte.attempts.append(
            model.Attempt(number=1, round=1, finding_ids=["F-307-01"], root_cause="c",
                          change_kind="logic", targets=["a.py::f"], diagnosis="d")
        )
        karte.results.append(
            model.Result(attempt=1, finding_ids=["F-307-01"], touched=["a.py", "a.py::f"],
                         outcome="partial", note="n")
        )
        parsed = model.parse(model.dumps(karte))
        self.assertEqual(parsed.issue, 307)
        self.assertEqual(parsed.findings[0].rounds, [1, 2])
        self.assertEqual(parsed.attempts[0].targets, ["a.py::f"])
        self.assertEqual(parsed.results[0].touched, ["a.py", "a.py::f"])

    def test_unparsable_line_is_rejected(self):
        with self.assertRaises(model.KarteFormatError):
            model.parse_blocks("### Attempt 1\nこれは key: value ではない行\n")

    def test_finding_id_format(self):
        self.assertEqual(model.format_finding_id(312, 3), "F-312-03")
        self.assertEqual(model.parse_finding_id("F-312-03"), (312, 3))
        with self.assertRaises(model.KarteFormatError):
            model.parse_finding_id("F-312-3")

    def test_max_consecutive_rounds(self):
        self.assertEqual(model.Finding(id="F-1-01", rounds=[1, 2, 4, 5, 6]).max_consecutive_rounds(), 3)
        self.assertEqual(model.Finding(id="F-1-01", rounds=[1, 3, 5]).max_consecutive_rounds(), 1)

    def test_list_item_with_comma_is_rejected(self):
        with self.assertRaises(model.KarteFormatError):
            model.check_list(["a,b"], "targets")


class TestSimilarity(unittest.TestCase):
    def _view(self, number, root_cause, change_kind, targets, touched=()):
        return similarity.AttemptView(number, root_cause, change_kind, tuple(targets), tuple(touched))

    def test_declared_signal_requires_same_root_cause(self):
        left = self._view(1, "a", "logic", ["x.py::f"])
        right = self._view(2, "b", "logic", ["x.py::f"])
        self.assertIsNone(similarity.compare(right, left))

    def test_declared_signal_via_change_kind(self):
        left = self._view(1, "a", "logic", ["x.py::f"])
        right = self._view(2, "a", "logic", ["y.py::g"])
        self.assertIsNotNone(similarity.compare(right, left))

    def test_declared_signal_via_target_overlap(self):
        left = self._view(1, "a", "logic", ["x.py::f"])
        right = self._view(2, "a", "config", ["x.py::f"])
        hit = similarity.compare(right, left)
        self.assertIsNotNone(hit)
        self.assertEqual(hit.overlapping_targets, ("x.py::f",))

    def test_declared_overlap_uses_prior_measured_touched(self):
        """宣言 targets が違っても、過去の実測 touched と重なれば交差とみなす。"""
        left = self._view(1, "a", "logic", ["x.py::f"], touched=["y.py", "y.py::g"])
        right = self._view(2, "a", "config", ["y.py::g"])
        self.assertIsNotNone(similarity.compare(right, left))

    def test_measured_signal_ignores_labels(self):
        left = self._view(1, "a", "logic", ["x.py::f"], touched=["x.py", "x.py::f"])
        right = self._view(2, "zzz", "revert", ["x.py::f"])
        hit = similarity.compare(right, left)
        self.assertIsNotNone(hit)
        self.assertFalse(hit.declared)
        self.assertTrue(hit.measured)

    def test_measured_signal_requires_a_measurement(self):
        """実測が片側にも無いなら、宣言 targets の一致だけで実測信号は名乗らせない。"""
        left = self._view(1, "a", "logic", ["x.py::f"])
        right = self._view(2, "b", "revert", ["x.py::f"])
        self.assertIsNone(similarity.compare(right, left))

    def test_saturation_threshold_is_two(self):
        self.assertFalse(similarity.is_saturated([object()]))
        self.assertTrue(similarity.is_saturated([object(), object()]))

    def test_overlap_matches_file_and_symbol_granularity(self):
        self.assertEqual(similarity.overlapping_entries(["x.py"], ["x.py::f"]), ["x.py"])
        self.assertEqual(similarity.overlapping_entries(["x.py::f"], ["x.py::g"]), [])


class TestTouchedFromDiff(unittest.TestCase):
    def test_collects_files_and_symbols(self):
        diff = (
            "diff --git a/pkg/forms.py b/pkg/forms.py\n"
            "--- a/pkg/forms.py\n"
            "+++ b/pkg/forms.py\n"
            "@@ -10,2 +10,3 @@ def build_attrs(self):\n"
            "-    old = 1\n"
            "+    new = 2\n"
            "@@ -30,0 +31,2 @@\n"
            "+def helper():\n"
            "+    return 1\n"
        )
        self.assertEqual(
            touched.parse_diff(diff),
            ["pkg/forms.py", "pkg/forms.py::build_attrs", "pkg/forms.py::helper"],
        )

    def test_deleted_file_uses_old_path(self):
        diff = "--- a/pkg/gone.py\n+++ /dev/null\n@@ -1,2 +0,0 @@\n-x = 1\n"
        self.assertEqual(touched.parse_diff(diff), ["pkg/gone.py"])

    def test_invalid_ref_is_rejected(self):
        with self.assertRaises(touched.TouchedError):
            touched.validate_ref("--output=/etc/passwd")


if __name__ == "__main__":
    unittest.main()
