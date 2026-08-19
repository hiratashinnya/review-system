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
import re
import inspect
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

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

    def _close_default_attempt(self, diff_text, outcome="partial", note="", tag="default"):
        """``--attempt`` を**省略**して ``close-attempt`` を呼ぶ（Issue #378 の既定値解決）。"""
        diff_path = self._write_report(f"diff-{tag}.patch", diff_text)
        return self._run(
            cli.cmd_close_attempt,
            attempt=None,
            outcome=outcome,
            finding_ids=None,
            base="HEAD",
            diff_file=diff_path,
            note=note,
        )

    def _karte(self):
        path = paths.karte_path(self.issue, self.root)
        return model.parse(path.read_text(encoding="utf-8"))

    def _karte_text(self) -> str:
        path = self.root / "tmp" / "_karte" / f"issue-{self.issue}.md"
        return path.read_text(encoding="utf-8") if path.is_file() else ""

    def _active_path(self) -> Path:
        return self.root / "tmp" / "_karte" / "active.json"

    def _run_with_stdin(self, func, stdin_text, **kwargs):
        """標準入力を差し替えて ``cmd_*`` を呼ぶ（``--from -`` の経路・K-13）。"""
        buffer = io.StringIO()
        errors = io.StringIO()
        with mock.patch.object(sys, "stdin", io.StringIO(stdin_text)):
            with contextlib.redirect_stdout(buffer), contextlib.redirect_stderr(errors):
                code = func(self._ns(**kwargs))
        return code, buffer.getvalue(), errors.getvalue()


HARMFUL = {
    "harm": "real",
    "harm_detail": "必須属性が消えて入力検証が素通りする",
    "severity": "blocker",
    "evidence": "a/b.py:12 を読み、attrs を辞書リテラルで作り直しているのを確認",
    "locus": "a/b.py::build_attrs",
    "summary": "build_attrs が既存 attrs を破棄している",
    "expected": "既存 attrs を保ったまま追加分だけマージする",
    "recheck": "required 付きフィールドを描画し required が残ることを確認する",
}
COSMETIC = {
    "harm": "none",
    "harm_detail": "表記ゆれのみで挙動に影響しない",
    "severity": "minor",
    "evidence": "docs/readme.md の見出しを読み、用語集と表記が違うのを確認",
    "locus": "docs/readme.md",
    "summary": "見出しの用語がゆれている",
    "expected": "用語が用語集の表記に揃っている",
    "recheck": "該当見出しを読んで表記が揃っていることを確認する",
}


class TestExplicitIssueWinsOverActivePointer(KarteTestCase):
    """Issue #354（K2）: `issue-fixer` は `karte_path` を受け取らず `--issue` を必ず明示する。

    その規律が実際に効くこと——**明示した `--issue` が進行ポインタより優先される**——を
    ここで固定する。ポインタ補完に落ちると、並行運用（別 Issue のラウンドが挟まる）で
    別 Issue の台帳を黙って書きうる。ポインタが「別 Issue」を指している状態を作り、
    明示側が勝つことを検査する。
    """

    def _point_active_at(self, issue, round_no=1):
        path = self._active_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps({"issue": issue, "round": round_no}) + "\n", encoding="utf-8"
        )

    def test_resolve_issue_prefers_the_explicit_flag(self):
        self._point_active_at(999)
        args = argparse.Namespace(issue=str(self.issue), repo_root=str(self.root))
        self.assertEqual(cli._resolve_issue(args), self.issue)
        # 省略した場合だけポインタへ落ちる（規律が「明示せよ」である理由そのもの）。
        fallback = argparse.Namespace(issue=None, repo_root=str(self.root))
        self.assertEqual(cli._resolve_issue(fallback), 999)

    def test_ingest_and_append_write_the_explicit_issues_karte(self):
        self._point_active_at(999, round_no=7)
        code, _out, err = self._ingest(1, ("new", HARMFUL))
        self.assertEqual(code, cli.EXIT_OK, err)
        code, _out, err = self._append(round="1")
        self.assertEqual(code, cli.EXIT_OK, err)
        self.assertIn("F-307-01", self._karte_text())
        self.assertFalse(
            (self.root / "tmp" / "_karte" / "issue-999.md").exists(),
            "明示した --issue ではなくポインタ側の Issue に書いてはならない",
        )


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

    def test_explicit_resolved_declaration_is_required_to_resolve(self):
        """K-06: 解消は ``status: resolved`` の**明示宣言**でだけ成立する。"""
        self._ingest(1, ("new", HARMFUL), ("new", COSMETIC))
        code, out, err = self._ingest(
            2, ("F-307-01", HARMFUL), ("F-307-02", dict(COSMETIC, status="resolved"))
        )
        self.assertEqual(code, cli.EXIT_OK, err)
        self.assertIn("F-307-02", out)
        karte = self._karte()
        self.assertEqual(karte.finding("F-307-02").status, "resolved")
        self.assertEqual(karte.finding("F-307-02").resolved_round, 2)
        self.assertEqual(karte.finding("F-307-01").status, "open")
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
        # F-307-01 を `status: resolved` で明示的に解消し（K-06）、別件 F-307-02 を挙げる。
        code, _out, err = self._ingest(
            2, ("F-307-01", dict(HARMFUL, status="resolved")), ("new", COSMETIC)
        )
        self.assertEqual(code, cli.EXIT_OK, err)
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

    def test_non_numeric_attempt_is_fail_closed_not_uncaught(self):
        """K-03: ``--attempt`` が非数値でも ``_fail_close`` の外（EXIT_ERROR 以外）に漏れない。

        是正前は ``int(args.attempt)`` が無検証で ``ValueError`` を送出し、``_fail_close``
        （5 種の例外しか捕まえない）を素通りして終了コードが文書化された
        ``{0,2,3,4}`` の外（未捕捉の例外＝1 相当）になっていた。
        """
        code, _out, err = self._close("abc", "--- a/x.py\n+++ b/x.py\n@@ -1 +1 @@\n-a\n+b\n")
        self.assertEqual(code, cli.EXIT_ERROR)
        self.assertIn("attempt", err)

    def test_zero_attempt_is_fail_closed(self):
        code, _out, err = self._close("0", "--- a/x.py\n+++ b/x.py\n@@ -1 +1 @@\n-a\n+b\n")
        self.assertEqual(code, cli.EXIT_ERROR)
        self.assertIn("attempt", err)

    def test_negative_attempt_is_fail_closed(self):
        code, _out, err = self._close("-1", "--- a/x.py\n+++ b/x.py\n@@ -1 +1 @@\n-a\n+b\n")
        self.assertEqual(code, cli.EXIT_ERROR)
        self.assertIn("attempt", err)


class TestCloseAttemptEmptyDiff(KarteTestCase):
    """Issue #355: 空 diff は ``--outcome no-change`` を除き fail-close する。

    是正前は既定 ``--base HEAD`` のまま commit・push 後に ``close-attempt`` を実行すると
    diff が空になり、``touched: []`` が append-only の台帳へ無言で固定されていた
    （PR #353 是正ラウンド1 で実際に発生）。
    """

    def setUp(self):
        super().setUp()
        self._ingest(1, ("new", HARMFUL))
        self._append(root_cause="cause-one", targets=["pkg/forms.py::build_attrs"])

    def test_empty_diff_is_rejected_for_fixed_outcome(self):
        code, _out, err = self._close(1, "", outcome="fixed")
        self.assertEqual(code, cli.EXIT_ERROR)
        self.assertIn("no-change", err)
        self.assertIn("空", err)
        # 拒否時は何も追記されない（fail-close）。
        self.assertEqual(self._karte().results_for(1), [])

    def test_empty_diff_is_rejected_for_partial_and_regressed_outcomes(self):
        for outcome in ("partial", "regressed"):
            with self.subTest(outcome=outcome):
                code, _out, err = self._close(1, "", outcome=outcome, note="")
                self.assertEqual(code, cli.EXIT_ERROR)
                self.assertIn("no-change", err)
                self.assertEqual(self._karte().results_for(1), [])

    def test_empty_diff_is_allowed_for_no_change_outcome(self):
        code, out, err = self._close(1, "", outcome="no-change", note="解釈違いで実装は元々正しかった")
        self.assertEqual(code, cli.EXIT_OK, err)
        self.assertIn("no-change", out)
        karte = self._karte()
        self.assertEqual(karte.results_for(1)[0].outcome, "no-change")
        self.assertEqual(karte.touched_of(1), [])

    def test_non_empty_diff_still_records_normally(self):
        """回帰防止：空 diff の拒否を足しても、通常の非空 diff は従来どおり通る。"""
        diff = "--- a/pkg/forms.py\n+++ b/pkg/forms.py\n@@ -1 +1 @@ def build_attrs(self):\n-x\n+y\n"
        code, _out, err = self._close(1, diff, outcome="fixed")
        self.assertEqual(code, cli.EXIT_OK, err)
        self.assertEqual(self._karte().touched_of(1), ["pkg/forms.py", "pkg/forms.py::build_attrs"])


class TestCloseAttemptDefaultAttemptResolution(KarteTestCase):
    """Issue #378: ``--attempt`` 省略時は未クローズ Attempt が1つのときだけ安全に解決する。

    以前は「直近で append された Attempt」（``next_attempt_number() - 1``）へ無条件に
    解決していたため、複数 Attempt を先に append してからまとめて close する運用で
    誤った Attempt へ記録される事故が2ラウンド連続で発生した（PR #364 是正ラウンド2・3）。
    """

    def setUp(self):
        super().setUp()
        self._ingest(1, ("new", HARMFUL))

    def _diff_for(self, name):
        return f"--- a/pkg/{name}.py\n+++ b/pkg/{name}.py\n@@ -1 +1 @@ def f(self):\n-x\n+y\n"

    def test_single_unclosed_attempt_is_used_even_when_not_the_latest(self):
        """未クローズが1つなら、それが最新でなくても曖昧でないので使う（後方互換の核）。"""
        self._append(root_cause="rc-1", targets=["pkg/m1.py::f1"])
        self._append(root_cause="rc-2", targets=["pkg/m2.py::f2"])
        code, _out, err = self._close(2, self._diff_for("m2"))  # Attempt 2 を先にクローズ
        self.assertEqual(code, cli.EXIT_OK, err)

        code, out, err = self._close_default_attempt(self._diff_for("m1"), outcome="fixed")
        self.assertEqual(code, cli.EXIT_OK, err)
        self.assertIn("Attempt 1", out)
        self.assertEqual(self._karte().results_for(1)[0].outcome, "fixed")

    def test_multiple_unclosed_attempts_require_explicit_attempt(self):
        self._append(root_cause="rc-1", targets=["pkg/m1.py::f1"])
        self._append(root_cause="rc-2", targets=["pkg/m2.py::f2"])
        code, _out, err = self._close_default_attempt(self._diff_for("m1"))
        self.assertEqual(code, cli.EXIT_ERROR)
        self.assertIn("Attempt 1", err)
        self.assertIn("Attempt 2", err)
        self.assertIn("--attempt", err)
        self.assertEqual(self._karte().results, [])  # 何も追記されない

    def test_zero_unclosed_attempts_gives_a_dedicated_message(self):
        """全てクローズ済みなら「既に Result がある」より前に、専用のメッセージで拒否する。"""
        self._append(root_cause="rc-1", targets=["pkg/m1.py::f1"])
        self._close(1, self._diff_for("m1"))
        code, _out, err = self._close_default_attempt(self._diff_for("m1"))
        self.assertEqual(code, cli.EXIT_ERROR)
        self.assertIn("クローズ済み", err)
        self.assertIn("--attempt", err)

    def test_zero_total_attempts_gives_a_distinct_message_from_all_closed(self):
        """F-378-01: Attempt が1件も無い場合は「全 Attempt が既にクローズ済み」と誤記しない。

        是正前は unclosed が空になる分岐（Attempt 0件 と 全件クローズ済み の両方を含む）で
        メッセージが後者だけを述べていた。setUp は ``_ingest`` のみで ``append`` を一度も
        呼んでいないため、ここは「Attempt が1件も無い」ケースそのもの。
        """
        self.assertEqual(self._karte().attempts, [])  # 前提: Attempt 0件
        code, _out, err = self._close_default_attempt(self._diff_for("m1"))
        self.assertEqual(code, cli.EXIT_ERROR)
        self.assertIn("--attempt", err)
        self.assertIn("1件も無い", err)
        # 「全 Attempt が既にクローズ済み」（事実と異なる）とは述べない。
        self.assertNotIn("クローズ済み", err)

    def test_explicit_attempt_still_overrides_default_resolution(self):
        """明示指定は常に優先される（既定解決ロジックをバイパスする）。"""
        self._append(root_cause="rc-1", targets=["pkg/m1.py::f1"])
        self._append(root_cause="rc-2", targets=["pkg/m2.py::f2"])
        code, _out, err = self._close(1, self._diff_for("m1"))  # 複数未クローズでも明示なら通る
        self.assertEqual(code, cli.EXIT_OK, err)
        self.assertEqual(self._karte().results_for(1)[0].attempt, 1)


class TestCloseAttemptHelpTextCoversAllThreeBranches(unittest.TestCase):
    """F-378-02: ``--attempt`` の ``--help`` が3分岐すべてを説明していること。

    是正前は「未クローズが1件ならそれを使う／2件以上なら拒否」の2分岐しか説明しておらず、
    「未クローズ0件（Attempt が1件も無い、または全件クローズ済み）でも fail-close する」
    という3つ目の分岐が欠けていた。``karte/README.md`` は既に3分岐を記載しているため、
    その非対称を固定する回帰テスト。
    """

    def test_help_text_mentions_the_zero_unclosed_branch(self):
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            with self.assertRaises(SystemExit):
                cli.build_parser().parse_args(["close-attempt", "--help"])
        help_text = buffer.getvalue()
        self.assertIn("2つ以上", help_text)  # 既存2分岐（複数未クローズ）を維持
        self.assertIn("0", help_text)        # 追加した3つ目の分岐（未クローズ0件）
        self.assertIn("拒否", help_text)


class TestCloseAttemptTargetTouchedMismatchWarning(KarteTestCase):
    """Issue #378 C: 宣言 targets と実測 touched の不一致は警告のみ（保険的検知・非ブロック）。"""

    def setUp(self):
        super().setUp()
        self._ingest(1, ("new", HARMFUL))
        self._append(root_cause="cause-one", targets=["pkg/forms.py::build_attrs"])

    def test_disjoint_targets_and_touched_emits_a_warning_but_still_succeeds(self):
        diff = "--- a/pkg/other.py\n+++ b/pkg/other.py\n@@ -1 +1 @@ def g(self):\n-x\n+y\n"
        code, out, err = self._close(1, diff, outcome="fixed")
        self.assertEqual(code, cli.EXIT_OK, err)  # 拒否しない（保険的検知）
        self.assertIn("重ならない", out)
        self.assertIn("pkg/forms.py::build_attrs", out)
        self.assertIn("pkg/other.py", out)
        self.assertEqual(self._karte().touched_of(1), ["pkg/other.py", "pkg/other.py::g"])

    def test_overlapping_targets_and_touched_emits_no_warning(self):
        diff = "--- a/pkg/forms.py\n+++ b/pkg/forms.py\n@@ -1 +1 @@ def build_attrs(self):\n-x\n+y\n"
        code, out, err = self._close(1, diff, outcome="fixed")
        self.assertEqual(code, cli.EXIT_OK, err)
        self.assertNotIn("重ならない", out)


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
        self._close(1, "--- a/a/b.py\n+++ b/a/b.py\n@@ -1 +1 @@ def f(self):\n-x\n+y\n")
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
        self._ingest(2, ("F-307-01", HARMFUL), ("new", COSMETIC))
        self._ingest(
            3,
            ("F-307-01", dict(HARMFUL, status="resolved")),
            ("F-307-02", dict(COSMETIC, status="resolved")),
        )
        karte = self._karte()
        self.assertEqual(karte.finding("F-307-01").status, "resolved")
        self.assertEqual(karte.finding("F-307-02").status, "resolved")
        code, out, _err = self._run(cli.cmd_status, json=False)
        self.assertEqual(code, cli.EXIT_OK)
        self.assertIn("clean", out)

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


class TestSeverityExpectedRecheck(KarteTestCase):
    """Issue #341 F-341-01: `pr-reviewer` が必須と宣言した3キーを台帳が実際に持つこと。

    以前は `pr-reviewer.md` が `severity`/`expected`/`recheck` を必須と書いていたのに
    `parse_review` がそれらを読まず `Finding` にも載っていなかったため、**欠落しても無言で通り**、
    2 ラウンド目以降に「どうなっていれば解消か（expected）」「何を実行して判定するか（recheck）」を
    台帳から復元できなかった。ここを固定する。
    """

    def test_missing_severity_expected_recheck_are_rejected(self):
        for missing in ("severity", "expected", "recheck"):
            with self.subTest(missing=missing):
                fields = {k: v for k, v in HARMFUL.items() if k != missing}
                code, _out, err = self._ingest(1, ("new", fields))
                self.assertNotEqual(code, cli.EXIT_OK, f"{missing} 欠落が素通りしている")
                self.assertIn(missing, err)

    def test_unknown_severity_is_rejected(self):
        fields = {**HARMFUL, "severity": "critical"}
        code, _out, err = self._ingest(1, ("new", fields))
        self.assertNotEqual(code, cli.EXIT_OK)
        self.assertIn("severity", err)

    def test_three_keys_survive_a_write_read_roundtrip(self):
        self._ingest(1, ("new", HARMFUL))
        finding = self._karte().findings[0]
        self.assertEqual(finding.severity, HARMFUL["severity"])
        self.assertEqual(finding.expected, HARMFUL["expected"])
        self.assertEqual(finding.recheck, HARMFUL["recheck"])

    def test_render_shows_expected_and_recheck_for_open_findings(self):
        # 是正側（issue-fixer）が前ラウンドの解消条件を引ける、が本キーを足した理由そのもの。
        self._ingest(1, ("new", HARMFUL))
        code, out, _err = self._run(cli.cmd_render)
        self.assertEqual(code, cli.EXIT_OK)
        self.assertIn(HARMFUL["expected"], out)
        self.assertIn(HARMFUL["recheck"], out)
        self.assertIn("severity=", out)

    def test_status_json_carries_the_three_keys(self):
        self._ingest(1, ("new", HARMFUL))
        code, out, _err = self._run(cli.cmd_status, json=True)
        self.assertEqual(code, cli.EXIT_OK)
        finding = json.loads(out)["findings"][0]
        self.assertEqual(finding["severity"], HARMFUL["severity"])
        self.assertEqual(finding["expected"], HARMFUL["expected"])
        self.assertEqual(finding["recheck"], HARMFUL["recheck"])

    def test_second_round_can_update_expected_and_recheck(self):
        # 同じ finding を再掲したとき、解消条件の更新が台帳へ反映される（据え置きではない）。
        self._ingest(1, ("new", HARMFUL))
        updated = {**HARMFUL, "expected": "別の期待に更新", "recheck": "別の再検証手順に更新"}
        code, _out, err = self._ingest(2, ("F-307-01", updated))
        self.assertEqual(code, cli.EXIT_OK, err)
        karte = self._karte()
        self.assertEqual(karte.findings[0].expected, "別の期待に更新")
        self.assertEqual(karte.findings[0].recheck, "別の再検証手順に更新")


class TestLocusListAndEvidence(KarteTestCase):
    """Issue #341 レビュー feedback: `locus` の複数箇所対応と `evidence` 欄。

    対称ミラー（`.claude/` ↔ `.codex/`）に同じ欠陥が出る本リポジトリでは、`locus` が 1 箇所しか
    持てないと**同一欠陥が複数 finding に分裂**し、未解消件数が水増しされて `status` の
    「同一 finding が N ラウンド連続未解消」判定まで歪む。実際に PR #341 のレビューで起きた。
    """

    def test_locus_accepts_a_list_of_places(self):
        mirrored = {**HARMFUL, "locus": "[.claude/agents/x.md::out, .codex/agents/x.toml::out]"}
        code, _out, err = self._ingest(1, ("new", mirrored))
        self.assertEqual(code, cli.EXIT_OK, err)
        finding = self._karte().findings[0]
        self.assertEqual(
            finding.locus, [".claude/agents/x.md::out", ".codex/agents/x.toml::out"]
        )

    def test_scalar_locus_is_normalized_to_a_single_element_list(self):
        # 1 箇所しか無いときに `[...]` を強制しない（書き味を落とさない）。
        self._ingest(1, ("new", HARMFUL))
        self.assertEqual(self._karte().findings[0].locus, [HARMFUL["locus"]])

    def test_one_finding_covers_mirrored_places_instead_of_splitting(self):
        # 2 箇所を 1 指摘で挙げれば未解消件数は 1。分裂させると 2 に水増しされる、が動機。
        mirrored = {**HARMFUL, "locus": "[a/x.md::out, b/x.toml::out]"}
        self._ingest(1, ("new", mirrored))
        code, out, _err = self._run(cli.cmd_status, json=True)
        self.assertEqual(code, cli.EXIT_OK)
        self.assertEqual(len(json.loads(out)["findings"]), 1)

    def test_reissued_id_is_detected_when_locus_only_partially_overlaps(self):
        # 前ラウンドで片方だけ直してミラー側が残った再掲を「別物」と誤判定しないこと
        # （完全一致ではなく交差で判定する理由）。
        self._ingest(1, ("new", {**HARMFUL, "locus": "[a/x.md::out, b/x.toml::out]"}))
        code, _out, err = self._ingest(2, ("new", {**HARMFUL, "locus": "b/x.toml::out"}))
        self.assertNotEqual(code, cli.EXIT_OK, "再発番が素通りしている")
        self.assertIn("再発番", err)

    def test_missing_evidence_is_rejected(self):
        fields = {k: v for k, v in HARMFUL.items() if k != "evidence"}
        code, _out, err = self._ingest(1, ("new", fields))
        self.assertNotEqual(code, cli.EXIT_OK, "evidence 欠落が素通りしている")
        self.assertIn("evidence", err)

    def test_evidence_survives_roundtrip_and_is_shown_by_render(self):
        self._ingest(1, ("new", HARMFUL))
        self.assertEqual(self._karte().findings[0].evidence, HARMFUL["evidence"])
        _code, out, _err = self._run(cli.cmd_render)
        self.assertIn(HARMFUL["evidence"], out)

    def test_harmless_findings_are_still_carried_in_the_ledger(self):
        # `harm: none` を握りつぶさない（据え置きはオーナー判断）ことを機械側でも固定する。
        self._ingest(1, ("new", COSMETIC))
        findings = self._karte().findings
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].harm, "none")
        self.assertEqual(findings[0].status, "open")
        # 再掲を省くと K-06 で取り込みごと拒否される＝黙って消せない。
        code, _out, err = self._ingest(2, ("new", HARMFUL))
        self.assertNotEqual(code, cli.EXIT_OK, "harm: none の指摘が黙って消えている")
        self.assertIn("F-307-01", err)


class TestLocusScalarIsCheckedLikeAListItem(unittest.TestCase):
    """PR #341 再レビュー round-2: `normalize_locus` のスカラ経路の文字検査。

    角括弧を省いて `locus: a.md::x, b.toml::x` と書くと、以前はスカラ 1 要素として受理され、
    `format_value` が `[a.md::x, b.toml::x]` と書き出すため**台帳を読み直した時点で 2 要素へ
    静かに割れた**。`is_same_finding` は locus の交差で再発番を判定するので、レポート側（1 要素）と
    台帳側（2 要素）で照合面がズレ、**同一指摘の再発番を見逃す**方向に効く＝locus を複数化した
    目的そのものを裏切る。fail-close で拒否することを固定する。
    """

    def test_scalar_locus_with_a_comma_is_rejected(self):
        for bad in ["a.md::x, b.toml::x", "a.md::x,b.toml::x"]:
            with self.subTest(value=bad):
                with self.assertRaises(model.KarteFormatError) as ctx:
                    model.normalize_locus(bad)
                self.assertIn("locus", str(ctx.exception))

    def test_scalar_locus_with_brackets_is_rejected(self):
        # `[` `]` も同様（リスト記法の書き損じが 1 要素として通ると同じ割れ方をする）。
        for bad in ["[a.md::x", "a.md::x]"]:
            with self.subTest(value=bad):
                with self.assertRaises(model.KarteFormatError):
                    model.normalize_locus(bad)

    def test_plain_scalar_locus_still_works(self):
        self.assertEqual(model.normalize_locus("a.md::x"), ["a.md::x"])
        self.assertEqual(model.normalize_locus(""), [])
        self.assertEqual(model.normalize_locus("  "), [])

    def test_locus_survives_a_ledger_roundtrip_without_changing_arity(self):
        # 受理された locus は台帳往復で要素数が変わらない（割れない）。
        for value in ["a.md::x", ["a.md::x"], ["a.md::x", "b.toml::x"]]:
            with self.subTest(value=value):
                finding = model.Finding(
                    id="F-341-01", harm="real", harm_detail="d", severity="major",
                    locus=model.normalize_locus(value), summary="s", evidence="e",
                    expected="x", recheck="r", rounds=[1],
                )
                block = model.parse_blocks(model.render_finding(finding))[0]
                self.assertEqual(
                    model.normalize_locus(block.fields["locus"]), finding.locus
                )


class TestFindingSchemaIsDeclaredConsistently(unittest.TestCase):
    """PR #341 再レビュー round-2: 宣言側（プロンプト・手順書）と実装側のキー集合の drift 検出。

    `evidence` を新設した際、`pr-reviewer` 定義2件だけを更新して配線側3ファイルを取り残した——
    F-341-01（`pr-reviewer` が必須と宣言したキーを実装が持っていなかった）と**まったく同じ型の
    drift が向きを変えて再発**した。人手の追従に頼らず機械で固定する。
    """

    ROOT = Path(__file__).resolve().parents[2]
    # 構造化 finding のキーを列挙している全ファイル（正本＋配線＋ミラー）。
    DECLARING_FILES = [
        # 正本。CLAUDE.md 本体から `.claude/rules/` へ分割された際にキー列挙も移動した
        # （Issue #387 / F-387-01）。検査対象を減らして緑にするのではなく、実体の宣言箇所を追う。
        ".claude/rules/05-skills-agents.md",
        ".claude/skills/issue-pipeline/SKILL.md",
        ".agents/skills/issue-pipeline/SKILL.md",
    ]

    def test_key_enumerations_match_the_parser(self):
        required = set(
            re.findall(
                r'_require_(?:enum|nonempty)\(block,\s*"([a-z_]+)"',
                inspect.getsource(model.parse_review),
            )
        )
        self.assertTrue(required, "parse_review から必須キーを抽出できていない")
        for name in self.DECLARING_FILES:
            with self.subTest(file=name):
                text = (self.ROOT / name).read_text(encoding="utf-8")
                enumerations = re.findall(
                    r"`harm`(?:/`[a-z_]+`)+", text
                )
                self.assertTrue(enumerations, f"{name} にキー列挙が見つからない")
                for enumeration in enumerations:
                    listed = set(re.findall(r"`([a-z_]+)`", enumeration))
                    missing = required - listed
                    self.assertFalse(
                        missing,
                        f"{name} のキー列挙が必須キー {sorted(missing)} を落としている"
                        f"（列挙: {enumeration}）",
                    )


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
        self.assertIn("飽和したアプローチ", out)
        self.assertIn("DIRECTIVE", out)

    def test_render_without_karte_is_not_found(self):
        """カルテ未作成は「未検出」であってガード違反ではない（EXIT_ERROR と区別する）。"""
        with contextlib.redirect_stderr(io.StringIO()) as errors:
            code = cli.main(["render", "--issue", "999"])
        self.assertEqual(code, cli.EXIT_NOT_FOUND)
        self.assertIn("未検出", errors.getvalue())


# --- K-02: close-attempt の呼び忘れで実測信号を無効化できない -------------------


class TestCheckRequiresClosedAttempts(KarteTestCase):
    """K-02: ``check`` は当該ラウンド以前の Attempt が全てクローズ済みであることを要求する。

    実測 touched-set の唯一の供給源が ``close-attempt`` なので、これを呼ばずに
    ``root_cause`` だけ書き換えて試行を重ねると、宣言信号（``root_cause`` 一致が必須）にも
    実測信号（測定値ゼロ）にも掛からず無制限に通ってしまう——偽装ではなく**呼び忘れだけ**で
    ゲートが無効化できた。``check`` は SubagentStop フックの判定根拠なので、ここで落とせば
    「クローズしないと前に進めない」になる。
    """

    def setUp(self):
        super().setUp()
        self._ingest(1, ("new", HARMFUL))

    def _diff_for(self, name):
        return f"--- a/pkg/{name}.py\n+++ b/pkg/{name}.py\n@@ -1 +1 @@ def f(self):\n-x\n+y\n"

    def test_unclosed_attempts_block_check(self):
        """close せずに root_cause を書き換えて重ねた試行は ``check`` で止まる。"""
        for index in range(1, 4):
            code, _out, err = self._append(
                root_cause=f"rc-{index}", targets=[f"pkg/m{index}.py::f{index}"]
            )
            self.assertEqual(code, cli.EXIT_OK, err)  # append 自体は通ってしまう
        self.assertEqual(len(self._karte().attempts), 3)

        code, _out, err = self._run(cli.cmd_check, round="1")
        self.assertEqual(code, cli.EXIT_ERROR)
        self.assertIn("未クローズ", err)
        for number in (1, 2, 3):
            self.assertIn(f"--attempt {number}", err)  # どれを閉じればよいか名指しする
        self.assertIn("close-attempt", err)

    def test_check_passes_once_every_attempt_is_closed(self):
        """クローズ済みなら通る（対で固定する）。"""
        self._append(root_cause="rc-1", targets=["pkg/m1.py::f1"])
        self._append(root_cause="rc-2", targets=["pkg/m2.py::f2"])
        self._close(1, self._diff_for("m1"))
        self._close(2, self._diff_for("m2"))
        code, out, err = self._run(cli.cmd_check, round="1")
        self.assertEqual(code, cli.EXIT_OK, err)
        self.assertIn("クローズ済み", out)

    def test_unclosed_attempt_from_an_earlier_round_also_blocks(self):
        """当該ラウンドだけでなく**それ以前**の未クローズ Attempt も落とす。"""
        self._append(root_cause="rc-1", targets=["pkg/m1.py::f1"])  # round 1・閉じない
        self._ingest(2, ("F-307-01", HARMFUL))
        self._append(round="2", root_cause="rc-2", targets=["pkg/m2.py::f2"])
        self._close(2, self._diff_for("m2"))
        code, _out, err = self._run(cli.cmd_check, round="2")
        self.assertEqual(code, cli.EXIT_ERROR)
        self.assertIn("--attempt 1", err)

    def test_unclosed_attempt_from_a_later_round_also_blocks(self):
        """**先のラウンド**を名乗った未クローズ Attempt も逃げ道にしない（PR #319 R-03）。

        是正前の pending 検査は ``round <= --round`` で絞っていたため、
        ``append --round <大きい値>`` で申告したラウンドを飛ばした Attempt は
        未クローズのまま ``check`` を通せた。既定経路では踏まないとしても、
        「呼ばれないと進まないように作る」を掲げる以上、呼び出し側がラウンドを
        正直に申告するという**暗黙の前提**にゲートを依存させない。
        """
        self._append(root_cause="rc-1", targets=["pkg/m1.py::f1"])  # round 1
        self._close(1, self._diff_for("m1"))
        self._append(round="9", root_cause="rc-9", targets=["pkg/m9.py::f9"])  # 未クローズ
        code, _out, err = self._run(cli.cmd_check, round="1")
        self.assertEqual(code, cli.EXIT_ERROR)
        self.assertIn("未クローズ", err)
        self.assertIn("--attempt 2", err)


# --- R-02: check の --round も進行ポインタから補完する ---------------------------


class TestCheckRoundFromActivePointer(KarteTestCase):
    """``check --round`` の省略を進行ポインタで補完する（PR #319 R-02）。

    K-02 で ``check`` は SubagentStop フックの判定根拠になったが、**フックは dispatch
    prompt を読めない**。他 4 verb は ``--issue``（``ingest-review``/``append`` は
    ``--round`` も）を補完できるのに ``check`` だけ ``required=True`` で非対称だったため、
    フック側にラウンド導出を再実装させることになっていた。
    """

    def setUp(self):
        super().setUp()
        self._ingest(1, ("new", HARMFUL))
        self._append(root_cause="rc-1", targets=["pkg/m1.py::f1"])
        self._close(1, "--- a/pkg/m1.py\n+++ b/pkg/m1.py\n@@ -1 +1 @@ def f1(self):\n-x\n+y\n")

    def test_round_is_filled_from_the_pointer(self):
        code, out, err = self._run(cli.cmd_check)
        self.assertEqual(code, cli.EXIT_OK, err)
        self.assertIn("round 1", out)

    def test_pointer_round_is_used_as_is_not_incremented(self):
        """``ingest-review`` と違って **+1 しない**（ポインタ＝いま是正中のラウンド）。"""
        self._ingest(2, ("F-307-01", HARMFUL))
        self._append(round="2", root_cause="rc-2", targets=["pkg/m2.py::f2"])
        self._close(2, "--- a/pkg/m2.py\n+++ b/pkg/m2.py\n@@ -1 +1 @@ def f2(self):\n-x\n+y\n")
        code, out, err = self._run(cli.cmd_check)
        self.assertEqual(code, cli.EXIT_OK, err)
        self.assertIn("round 2", out)
        self.assertNotIn("round 3", out)

    def test_explicit_round_still_wins(self):
        """明示指定はポインタ（round 1・この構成では OK になる）より優先される。"""
        code, out, _err = self._run(cli.cmd_check, round="2")
        self.assertEqual(code, cli.EXIT_ERROR)  # round 2 の Attempt はまだ無い
        self.assertIn("round 2", out)

    def test_missing_active_pointer_is_fail_closed(self):
        """不在は他 verb と同じ ``EXIT_ERROR``（ラウンドを推測しない）。"""
        self._active_path().unlink()
        code, _out, err = self._run(cli.cmd_check)
        self.assertEqual(code, cli.EXIT_ERROR)
        self.assertIn("進行ポインタ", err)

    def test_broken_active_pointer_is_fail_closed(self):
        self._active_path().write_text("{ broken", encoding="utf-8")
        code, _out, err = self._run(cli.cmd_check)
        self.assertEqual(code, cli.EXIT_ERROR)
        self.assertIn("壊れている", err)

    def test_pointer_without_round_is_fail_closed(self):
        self._active_path().write_text('{"issue": 307}', encoding="utf-8")
        code, _out, err = self._run(cli.cmd_check)
        self.assertEqual(code, cli.EXIT_ERROR)
        self.assertIn("'round'", err)

    def test_pointer_pointing_at_another_issue_is_fail_closed(self):
        self._active_path().write_text('{"issue": 999, "round": 4}', encoding="utf-8")
        code, _out, err = self._run(cli.cmd_check)
        self.assertEqual(code, cli.EXIT_ERROR)
        self.assertIn("食い違う", err)

    def test_round_is_not_required_on_the_cli_surface(self):
        """argparse が ``--round`` 無しの ``check`` を受け付ける（フックが叩ける形）。"""
        args = cli.build_parser().parse_args(["check", "--issue", "307"])
        self.assertIsNone(args.round)
        self.assertIs(args.func, cli.cmd_check)


# --- K-06: 「不在＝解消」の廃止 -------------------------------------------------


class TestAbsentFindingIsRejected(KarteTestCase):
    """K-06: 前ラウンドで未解消だった finding の**不在**は解消ではない（fail-close）。

    是正前は再掲されなかった finding を無条件 resolved にしていたため、部分的なレポートを
    1 回取り込むだけで ``harm: real`` の指摘が消え ``status`` が ``clean`` を返した
    （fail-open）。CLAUDE.md「指摘は処置完了まで追う」と正面から擦れる。
    """

    THIRD = {
        "harm": "real",
        "harm_detail": "境界値でインデックスが 1 ずれる",
        "severity": "major",
        "evidence": "境界値のテストを実行して失敗を確認",
        "expected": "境界値でもインデックスがずれない",
        "recheck": "境界値のテストケースを実行して通ることを確認する",
        "locus": "pkg/slicer.py::take",
        "summary": "take が末尾要素を取りこぼす",
    }

    def setUp(self):
        super().setUp()
        self._ingest(1, ("new", HARMFUL), ("new", COSMETIC), ("new", self.THIRD))

    def test_absent_open_finding_is_rejected_and_karte_is_untouched(self):
        before = self._karte_text()
        code, _out, err = self._ingest(2, ("F-307-01", HARMFUL))
        self.assertEqual(code, cli.EXIT_ERROR)
        self.assertIn("再掲されていない", err)
        self.assertIn("F-307-02", err)
        self.assertIn("F-307-03", err)  # 欠けている ID を**全て**列挙する
        self.assertEqual(self._karte_text(), before)  # カルテは一切書き換えない

    def test_harm_none_is_not_exempted(self):
        """``harm: none`` だけ緩めない（そこが抜け道になる）。"""
        code, _out, err = self._ingest(
            2, ("F-307-01", HARMFUL), ("F-307-03", self.THIRD)
        )
        self.assertEqual(code, cli.EXIT_ERROR)
        self.assertIn("F-307-02", err)  # COSMETIC＝harm none も再掲必須

    def test_explicit_resolved_is_the_only_way_to_close(self):
        code, out, err = self._ingest(
            2,
            ("F-307-01", HARMFUL),
            ("F-307-02", dict(COSMETIC, status="resolved")),
            ("F-307-03", dict(self.THIRD, status="resolved")),
        )
        self.assertEqual(code, cli.EXIT_OK, err)
        self.assertIn("F-307-02", out)
        karte = self._karte()
        self.assertEqual(karte.finding("F-307-02").status, "resolved")
        self.assertEqual(karte.finding("F-307-03").resolved_round, 2)
        self.assertEqual([item.id for item in karte.open_findings()], ["F-307-01"])

    def test_misspelled_status_is_rejected_not_defaulted(self):
        code, _out, err = self._ingest(
            2,
            ("F-307-01", HARMFUL),
            ("F-307-02", dict(COSMETIC, status="resolve")),
            ("F-307-03", self.THIRD),
        )
        self.assertEqual(code, cli.EXIT_ERROR)
        self.assertIn("status", err)


# --- K-05: 再発番検出の偽陽性に対するペア限定エスケープハッチ --------------------


DUP_A = {
    "harm": "real",
    "harm_detail": "重複 ID を弾けず台帳が二重登録される",
    "severity": "major",
    "evidence": "重複 ID のレポートを取り込んで通ることを確認",
    "expected": "重複 ID を検出して取り込みを拒否する",
    "recheck": "重複 ID を含むレポートを取り込んで拒否されることを確認する",
    "locus": "karte/cli.py::cmd_ingest_review",
    "summary": "cmd_ingest_review が finding ID の重複を見ていない",
}
DUP_B = {
    "harm": "real",
    "harm_detail": "欠落した ID を検出できず指摘が消える",
    "severity": "major",
    "evidence": "ID を欠いたレポートを取り込んで通ることを確認",
    "expected": "欠落した ID を検出して取り込みを拒否する",
    "recheck": "ID を欠いたレポートを取り込んで拒否されることを確認する",
    "locus": "karte/cli.py::cmd_ingest_review",
    "summary": "cmd_ingest_review が finding ID の欠落を見ていない",
}
DUP_C = {
    "harm": "real",
    "harm_detail": "順序が崩れて採番が飛ぶ",
    "severity": "minor",
    "evidence": "連続取り込みで ID が飛ぶのを確認",
    "expected": "採番が連番のまま保たれる",
    "recheck": "連続して取り込み ID が飛んでいないことを確認する",
    "locus": "karte/cli.py::cmd_ingest_review",
    "summary": "cmd_ingest_review が finding ID の順序を見ていない",
}


class TestDistinctFromEscapeHatch(KarteTestCase):
    """K-05: 同一 locus の別指摘が偽陽性で弾かれたときの**明示的な**逃げ道。

    同一 locus に複数の指摘が出るのは実務上ふつうで、語尾違いの短い要約同士は
    bigram Jaccard 0.6 を超えうる。是正前はその瞬間にレポート全体が ``EXIT_ERROR`` になり、
    上書きも否認もできず**正当な新規指摘を起票できなかった**。
    """

    def setUp(self):
        super().setUp()
        self._ingest(1, ("new", DUP_A))

    def test_threshold_is_not_relaxed(self):
        """閾値は動かさない（通すための調整をしない）。"""
        self.assertEqual(model.DUPLICATE_SIMILARITY_THRESHOLD, 0.6)
        self.assertTrue(
            model.is_same_finding(
                DUP_A["summary"], DUP_A["locus"], DUP_B["summary"], DUP_B["locus"]
            )
        )

    def test_false_positive_is_rejected_without_the_hatch(self):
        code, _out, err = self._ingest(2, ("F-307-01", DUP_A), ("new", DUP_B))
        self.assertEqual(code, cli.EXIT_ERROR)
        self.assertIn("ID 再発番", err)
        self.assertIn("distinct_from", err)  # 逃げ道の書き方を示す

    def test_named_pair_is_accepted(self):
        code, out, err = self._ingest(
            2, ("F-307-01", DUP_A), ("new", dict(DUP_B, distinct_from="F-307-01"))
        )
        self.assertEqual(code, cli.EXIT_OK, err)
        self.assertIn("F-307-02", out)
        self.assertIn("distinct_from", out)  # 監査できるよう出力に残す
        self.assertEqual([item.id for item in self._karte().findings], ["F-307-01", "F-307-02"])

    def test_hatch_applies_only_to_the_named_pair(self):
        """判定そのものは無効化しない（名指ししていない相手には効き続ける）。"""
        self._ingest(2, ("F-307-01", DUP_A), ("new", dict(DUP_B, distinct_from="F-307-01")))
        code, _out, err = self._ingest(
            3,
            ("F-307-01", DUP_A),
            ("F-307-02", DUP_B),
            ("new", dict(DUP_C, distinct_from="F-307-01")),
        )
        self.assertEqual(code, cli.EXIT_ERROR)
        self.assertIn("ID 再発番", err)
        self.assertIn("F-307-02", err)  # 名指ししていない F-307-02 とは依然として衝突

    def test_unknown_reference_is_rejected(self):
        code, _out, err = self._ingest(
            2, ("F-307-01", DUP_A), ("new", dict(DUP_B, distinct_from="F-307-42"))
        )
        self.assertEqual(code, cli.EXIT_ERROR)
        self.assertIn("実在しない", err)

    def test_self_reference_is_rejected(self):
        code, _out, err = self._ingest(
            2, ("F-307-01", dict(DUP_A, distinct_from="F-307-01"))
        )
        self.assertEqual(code, cli.EXIT_ERROR)
        self.assertIn("自分自身", err)

    def test_reference_to_another_issue_is_rejected(self):
        code, _out, err = self._ingest(
            2, ("F-307-01", DUP_A), ("new", dict(DUP_B, distinct_from="F-999-01"))
        )
        self.assertEqual(code, cli.EXIT_ERROR)
        self.assertIn("issue", err)


# --- K-09: 表示（render/status）とゲート（append）の判定を一本化 ----------------


class TestSaturationDisplayMatchesGate(KarteTestCase):
    """K-09: ``render``/``status`` の飽和表示は「同種の再試行が拒否される」を意味する。

    是正前は表示側だけが union-find の連結成分を使っており、推移律で広がるクラスタと
    ``append`` の pairwise 件数が食い違った——A1(rc=x, logic, T1) と A2(rc=x, logic, T2) は
    change_kind 経由で 1 クラスタになる一方、A3(rc=x, interface, T2) は A2 とのみ類似
    （hits=1）なので ``append`` は通る。「``render`` が飽和と言った直後に ``append`` が
    成功する」状態で、後工程が表示を「次の append が落ちる」と誤読した。
    """

    def setUp(self):
        super().setUp()
        self._ingest(1, ("new", HARMFUL))
        self._append(root_cause="rc-x", change_kind="logic", targets=["pkg/a.py::f"])
        self._append(root_cause="rc-x", change_kind="logic", targets=["pkg/b.py::g"])

    def test_display_group_is_shown_for_the_saturated_approach(self):
        code, out, err = self._run(cli.cmd_render)
        self.assertEqual(code, cli.EXIT_OK, err)
        self.assertIn("飽和したアプローチ", out)
        self.assertIn("同種の再試行は append が拒否される", out)
        self.assertIn("Attempt 1, 2", out)
        # 表示が何を意味しないかも本文で明示する（誤読の防止が K-09 の主眼）。
        self.assertIn("次の append が必ず落ちる」という意味ではなく", out)

    def test_same_approach_append_is_actually_rejected(self):
        """表示どおり、同種の再試行は拒否される。"""
        code, out, _err = self._append(
            root_cause="rc-x", change_kind="logic", targets=["pkg/a.py::f"]
        )
        self.assertEqual(code, cli.EXIT_SATURATED)
        self.assertIn("DIRECTIVE", out)
        self.assertEqual(len(self._karte().attempts), 2)

    def test_different_approach_append_is_allowed_and_not_displayed_as_saturated(self):
        """A3(rc=x, interface, T2) は A2 としか類似しないので通る（表示とも矛盾しない）。"""
        _code, before, _err = self._run(cli.cmd_render)
        self.assertNotIn(
            "root_cause=rc-x / change_kind=interface", before
        )  # 表示は logic 系のアプローチだけを飽和と言っている

        code, _out, err = self._append(
            root_cause="rc-x", change_kind="interface", targets=["pkg/b.py::g"]
        )
        self.assertEqual(code, cli.EXIT_OK, err)
        self.assertEqual(len(self._karte().attempts), 3)

    def test_status_groups_use_the_same_judgment(self):
        _code, out, _err = self._run(cli.cmd_status, json=True)
        payload = json.loads(out)
        self.assertEqual(payload["saturated_groups"], [[1, 2]])
        self.assertTrue(payload["escalate"])

    def test_only_one_similarity_judgment_exists(self):
        """2 つ目の類似判定（連結成分）を復活させない（再発防止）。"""
        self.assertFalse(hasattr(similarity, "cluster"))
        self.assertFalse(hasattr(cli, "_similar_clusters"))

    def test_display_hits_come_from_the_gate_input_set(self):
        """判定関数だけでなく**入力集合**も ``append`` と同じであること（PR #319 R-01）。"""
        karte = self._karte()
        for number, _members, hits, _candidate in cli._saturated_groups(karte):
            gate_priors = {
                view.number
                for view in cli._priors_for(karte, karte.attempt(number).finding_ids)
            }
            with self.subTest(candidate=number):
                self.assertTrue({hit.prior for hit in hits} <= gate_priors)


class TestSaturationScopeIsPerCandidate(KarteTestCase):
    """K-09 の第2の穴: 表示側の priors が候補ごとにスコープされていなかった（PR #319 R-01）。

    判定関数（``find_hits`` ＋ ``is_saturated``）は 1 つでも、**入力集合が 2 通り**あれば
    表示とゲートは食い違う。是正前の ``_saturated_groups`` は priors に「未解消 finding を
    **どれか**共有する全 Attempt」を使い、``append`` は ``_priors_for``（＝候補が対象とする
    未解消 finding を共有する Attempt）を使っていた。

    そのため未解消 finding が 2 件あり Attempt を finding ごとに分けると:
      * 過大報告 … finding B の Attempt が finding A の試行まで数えられて飽和表示されるのに、
        同じアプローチの ``append`` は ``EXIT_OK`` で通る。
      * 過少報告 … その裏返し（``append`` は拒否するのに ``escalate: no`` のまま表示に出ない）。

    ここでは (a) 表示された members の再試行が実際に ``EXIT_SATURATED`` になること、
    (b) 表示されない Attempt の再試行が ``EXIT_OK`` で通ること、を**対で**固定する。
    """

    def setUp(self):
        super().setUp()
        self._ingest(1, ("new", HARMFUL), ("new", COSMETIC))  # F-307-01 / F-307-02 とも未解消
        # F-307-01 に対して同種を 2 件 ＝ このアプローチは飽和した。
        self._append(
            finding_ids=["F-307-01"], root_cause="rc-x", change_kind="logic",
            targets=["pkg/a.py::f"],
        )
        self._append(
            finding_ids=["F-307-01"], root_cause="rc-x", change_kind="logic",
            targets=["pkg/b.py::g"],
        )
        # F-307-02 に対しては同じ宣言でもまだ 1 件目 ＝ 飽和していない。
        self._append(
            finding_ids=["F-307-02"], root_cause="rc-x", change_kind="logic",
            targets=["pkg/c.py::h"],
        )
        self.assertEqual(len(self._karte().attempts), 3)

    def _retry(self, attempt):
        """``attempt`` の宣言をそのまま繰り返す再試行を ``append`` する。"""
        return self._append(
            finding_ids=list(attempt.finding_ids),
            root_cause=attempt.root_cause,
            change_kind=attempt.change_kind,
            targets=list(attempt.targets),
        )

    def test_groups_are_scoped_to_the_candidate_finding_ids(self):
        _code, out, _err = self._run(cli.cmd_status, json=True)
        payload = json.loads(out)
        # 是正前は [[1, 2, 3]]（F-307-02 の Attempt 3 まで巻き込んでいた）。
        self.assertEqual(payload["saturated_groups"], [[1, 2]])
        self.assertTrue(payload["escalate"])

    def test_every_displayed_member_is_actually_rejected_by_append(self):
        """(a) 表示された members の再試行は必ず ``EXIT_SATURATED``。"""
        karte = self._karte()
        groups = cli._saturated_groups(karte)
        self.assertTrue(groups, "飽和グループが 1 つも出ていない（前提が崩れている）")
        for _number, members, _hits, _candidate in groups:
            for member in members:
                with self.subTest(member=member):
                    code, out, err = self._retry(karte.attempt(member))
                    self.assertEqual(code, cli.EXIT_SATURATED, out + err)
                    self.assertIn("DIRECTIVE", out)
        self.assertEqual(len(self._karte().attempts), 3)  # 拒否時は書き込まない

    def test_attempts_outside_the_displayed_groups_can_still_append(self):
        """(b) 表示されない Attempt の再試行は ``EXIT_OK`` で通る。"""
        karte = self._karte()
        gated = {
            member
            for _number, members, _hits, _candidate in cli._saturated_groups(karte)
            for member in members
        }
        self.assertNotIn(3, gated)  # 是正前は 3 も飽和扱いされていた
        code, _out, err = self._retry(karte.attempt(3))
        self.assertEqual(code, cli.EXIT_OK, err)
        self.assertEqual(len(self._karte().attempts), 4)

    def test_render_names_only_the_saturated_approach(self):
        _code, out, _err = self._run(cli.cmd_render)
        self.assertIn("飽和したアプローチ", out)
        self.assertIn("衝突する既存 Attempt 1, 2", out)
        self.assertNotIn("衝突する既存 Attempt 1, 2, 3", out)
        self.assertNotIn("Attempt 3 と同種", out)


# --- K-12: `_REPO_ROOT` の遅延評価 ----------------------------------------------


class TestRepoRootIsResolvedLazily(unittest.TestCase):
    """K-12: 壊れた ``.git`` でも終了コードが文書化範囲 ``{0,2,3,4}`` の外へ漏れない。

    ``main_worktree_root`` は ``.git`` ファイルが ``gitdir:`` で始まらなければ
    :class:`paths.KartePathError` を送出する。是正前はこれを**モジュールレベル**で
    評価していたため、例外はどの ``cmd_*``（``_fail_close`` でラップ済み）の内側でもない
    **import 時**に飛び、``python3 -m karte <任意の verb>`` が未捕捉例外で終了した。
    """

    def setUp(self):
        self.broken = Path(tempfile.mkdtemp(prefix="karte-brokengit-")).resolve()
        self.addCleanup(lambda: shutil.rmtree(self.broken, ignore_errors=True))
        (self.broken / "tmp").mkdir()
        (self.broken / ".git").write_text("this-is-not-a-gitdir-line\n", encoding="utf-8")

    def test_module_level_repo_root_is_not_evaluated_at_import(self):
        self.assertIsNone(cli._REPO_ROOT)

    def test_main_returns_exit_error_without_traceback(self):
        errors = io.StringIO()
        with mock.patch.object(cli, "_PACKAGE_ROOT", self.broken):
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(errors):
                code = cli.main(["status", "--issue", "1"])
        self.assertEqual(code, cli.EXIT_ERROR)
        self.assertIn("拒否（fail-close）", errors.getvalue())
        self.assertNotIn("Traceback", errors.getvalue())

    def test_direct_cmd_call_is_fail_closed_too(self):
        """``cmd_*`` 直呼び経路でも同じ（ガードの効力を呼び出し経路に依存させない）。"""
        for func, kwargs in (
            (cli.cmd_status, {"json": False}),
            (cli.cmd_render, {}),
            (cli.cmd_check, {"round": "1"}),
        ):
            with self.subTest(func=func.__name__):
                errors = io.StringIO()
                args = argparse.Namespace(issue="1", **kwargs)
                with mock.patch.object(cli, "_PACKAGE_ROOT", self.broken):
                    with contextlib.redirect_stdout(io.StringIO()):
                        with contextlib.redirect_stderr(errors):
                            code = func(args)
                self.assertEqual(code, cli.EXIT_ERROR)
                self.assertNotIn("Traceback", errors.getvalue())

    def test_every_verb_over_argv_stays_within_documented_exit_codes(self):
        argv_cases = (
            ["render", "--issue", "1"],
            ["status", "--issue", "1"],
            ["check", "--issue", "1", "--round", "1"],
            ["ingest-review", "--issue", "1", "--round", "1", "--from", "review.md"],
            ["close-attempt", "--issue", "1", "--outcome", "fixed"],
            ["append", "--issue", "1", "--finding-ids", "F-1-01", "--root-cause", "c",
             "--change-kind", "logic", "--targets", "a.py::f"],
        )
        for argv in argv_cases:
            with self.subTest(verb=argv[0]):
                with mock.patch.object(cli, "_PACKAGE_ROOT", self.broken):
                    with contextlib.redirect_stdout(io.StringIO()):
                        with contextlib.redirect_stderr(io.StringIO()):
                            code = cli.main(argv)
                self.assertIn(code, (cli.EXIT_OK, cli.EXIT_NOT_FOUND,
                                     cli.EXIT_SATURATED, cli.EXIT_ERROR))


# --- K-13: ingest-review を stdin から受け取る ----------------------------------


class TestIngestFromStdin(KarteTestCase):
    """K-13: SubagentStop フックが ``last_assistant_message`` を直接食わせる受け口。

    当初設計の「``pr-reviewer`` がチャットで返す → 主文脈がファイル化して ``ingest-review``」
    には (a) 主文脈が写し間違える余地、(b) 主文脈が忘れたら台帳に入らない、という
    二重の穴があった。stdin 経路でも検証は**同じように効く**。
    """

    def test_report_is_read_from_stdin(self):
        code, out, err = self._run_with_stdin(
            cli.cmd_ingest_review, _report(("new", HARMFUL)), round="1", source="-"
        )
        self.assertEqual(code, cli.EXIT_OK, err)
        self.assertIn("F-307-01", out)
        self.assertEqual([item.id for item in self._karte().findings], ["F-307-01"])

    def test_issue_and_round_are_filled_from_active_pointer(self):
        self._ingest(1, ("new", HARMFUL))
        code, out, err = self._run_with_stdin(
            cli.cmd_ingest_review,
            _report(("F-307-01", HARMFUL)),
            issue=None,
            round=None,
            source="-",
        )
        self.assertEqual(code, cli.EXIT_OK, err)
        self.assertIn("round 2", out)  # ポインタが指す最後のラウンドの次
        self.assertEqual(self._karte().finding("F-307-01").rounds, [1, 2])
        self.assertEqual(
            json.loads(self._active_path().read_text(encoding="utf-8")),
            {"issue": 307, "round": 2},
        )

    def test_missing_active_pointer_is_fail_closed(self):
        code, _out, err = self._run_with_stdin(
            cli.cmd_ingest_review,
            _report(("new", HARMFUL)),
            issue=None,
            round=None,
            source="-",
        )
        self.assertEqual(code, cli.EXIT_ERROR)
        self.assertIn("進行ポインタ", err)
        self.assertFalse((self.root / "tmp" / "_karte").exists())

    def test_broken_active_pointer_is_fail_closed(self):
        self._ingest(1, ("new", HARMFUL))
        self._active_path().write_text("{ not json", encoding="utf-8")
        before = self._karte_text()
        code, _out, err = self._run_with_stdin(
            cli.cmd_ingest_review,
            _report(("F-307-01", HARMFUL)),
            issue=None,
            round=None,
            source="-",
        )
        self.assertEqual(code, cli.EXIT_ERROR)
        self.assertIn("壊れている", err)
        self.assertEqual(self._karte_text(), before)

    def test_active_pointer_without_round_is_fail_closed(self):
        self._ingest(1, ("new", HARMFUL))
        self._active_path().write_text('{"issue": 307}', encoding="utf-8")
        code, _out, err = self._run_with_stdin(
            cli.cmd_ingest_review,
            _report(("F-307-01", HARMFUL)),
            issue=None,
            round=None,
            source="-",
        )
        self.assertEqual(code, cli.EXIT_ERROR)
        self.assertIn("round", err)

    def test_active_pointer_pointing_at_another_issue_is_fail_closed(self):
        self._ingest(1, ("new", HARMFUL))
        self._active_path().write_text('{"issue": 999, "round": 1}', encoding="utf-8")
        code, _out, err = self._run_with_stdin(
            cli.cmd_ingest_review, _report(("F-307-01", HARMFUL)), round=None, source="-"
        )
        self.assertEqual(code, cli.EXIT_ERROR)
        self.assertIn("食い違", err)

    def test_empty_stdin_is_fail_closed(self):
        code, _out, err = self._run_with_stdin(
            cli.cmd_ingest_review, "   \n", round="1", source="-"
        )
        self.assertEqual(code, cli.EXIT_ERROR)
        self.assertIn("空", err)
        self.assertFalse((self.root / "tmp" / "_karte").exists())

    def test_unreadable_stdin_is_fail_closed(self):
        """標準入力が無い（``sys.stdin is None``）状態でも未捕捉例外にしない。"""
        errors = io.StringIO()
        with mock.patch.object(sys, "stdin", None):
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(errors):
                code = cli.cmd_ingest_review(self._ns(round="1", source="-"))
        self.assertEqual(code, cli.EXIT_ERROR)
        self.assertIn("標準入力", errors.getvalue())

    def test_absence_prohibition_still_applies_on_the_stdin_path(self):
        """K-06 の不在禁止は stdin 経路でも同じように効く。"""
        self._ingest(1, ("new", HARMFUL), ("new", COSMETIC))
        before = self._karte_text()
        code, _out, err = self._run_with_stdin(
            cli.cmd_ingest_review,
            _report(("F-307-01", HARMFUL)),
            issue=None,
            round=None,
            source="-",
        )
        self.assertEqual(code, cli.EXIT_ERROR)
        self.assertIn("F-307-02", err)
        self.assertEqual(self._karte_text(), before)

    def test_duplicate_ids_and_missing_harm_still_rejected_on_the_stdin_path(self):
        self._ingest(1, ("new", HARMFUL))
        code, _out, err = self._run_with_stdin(
            cli.cmd_ingest_review,
            _report(("F-307-01", HARMFUL), ("F-307-01", HARMFUL)),
            round="2",
            source="-",
        )
        self.assertEqual(code, cli.EXIT_ERROR)
        self.assertIn("重複", err)

        broken = dict(HARMFUL)
        del broken["harm"]
        code, _out, err = self._run_with_stdin(
            cli.cmd_ingest_review, _report(("F-307-01", broken)), round="2", source="-"
        )
        self.assertEqual(code, cli.EXIT_ERROR)
        self.assertIn("harm", err)

    def test_distinct_from_hatch_still_works_on_the_stdin_path(self):
        self._ingest(1, ("new", DUP_A))
        code, out, err = self._run_with_stdin(
            cli.cmd_ingest_review,
            _report(("F-307-01", DUP_A), ("new", dict(DUP_B, distinct_from="F-307-01"))),
            round="2",
            source="-",
        )
        self.assertEqual(code, cli.EXIT_OK, err)
        self.assertIn("F-307-02", out)

    def test_stdin_over_argv(self):
        """公開 CLI 面（``--from -``）でも通ること。"""
        buffer = io.StringIO()
        errors = io.StringIO()
        with mock.patch.object(cli, "_REPO_ROOT", self.root):
            with mock.patch.object(sys, "stdin", io.StringIO(_report(("new", HARMFUL)))):
                with contextlib.redirect_stdout(buffer), contextlib.redirect_stderr(errors):
                    code = cli.main(["ingest-review", "--issue", "307", "--round", "1",
                                     "--from", "-"])
        self.assertEqual(code, cli.EXIT_OK, errors.getvalue())
        self.assertIn("F-307-01", buffer.getvalue())


# --- K-14: render をフックが注入しやすい形にする --------------------------------


class TestRenderForInjection(KarteTestCase):
    """K-14: SubagentStart フックが ``additionalContext`` としてそのまま注入できる本文。"""

    def test_issue_is_filled_from_active_pointer(self):
        self._ingest(1, ("new", HARMFUL))
        self._append(root_cause="attrs-overwrite", targets=["pkg/forms.py::build_attrs"])
        code, out, err = self._run(cli.cmd_render, issue=None)
        self.assertEqual(code, cli.EXIT_OK, err)
        self.assertIn("issue-307", out)
        self.assertIn("Attempt 1", out)

    def test_missing_active_pointer_is_fail_closed(self):
        code, _out, err = self._run(cli.cmd_render, issue=None)
        self.assertEqual(code, cli.EXIT_ERROR)
        self.assertIn("進行ポインタ", err)

    def test_broken_active_pointer_is_fail_closed(self):
        self._ingest(1, ("new", HARMFUL))
        self._active_path().write_text("[]", encoding="utf-8")
        code, _out, err = self._run(cli.cmd_render, issue=None)
        self.assertEqual(code, cli.EXIT_ERROR)
        self.assertIn("進行ポインタ", err)

    def test_output_is_self_contained(self):
        self._ingest(1, ("new", HARMFUL), ("new", COSMETIC))
        self._append(
            finding_ids=["F-307-01"], root_cause="attrs-overwrite",
            targets=["pkg/forms.py::build_attrs"], diagnosis="既存 attrs を作り直している",
        )
        self._close(
            1, "--- a/pkg/forms.py\n+++ b/pkg/forms.py\n@@ -1 +1 @@ def build_attrs(self):\n-x\n+y\n"
        )
        code, out, err = self._run(cli.cmd_render, issue=None)
        self.assertEqual(code, cli.EXIT_OK, err)

        # 何の本文か・どこから来たか（前後の文脈に依存しない）。
        self.assertIn("Issue #307", out)
        self.assertIn("issue-307.md", out)
        # 受け手が次に何をすべきか（呼ぶべきコマンドを含む）。
        self.assertIn("python3 -m karte append", out)
        self.assertIn("python3 -m karte close-attempt", out)
        # 過去 Attempt（実測・Result 込み）と未解消 finding の一覧。
        self.assertIn("## Prior attempts（DO NOT repeat these）", out)
        self.assertIn("実測 touched: pkg/forms.py", out)
        self.assertIn("→ Result: partial", out)
        self.assertIn("## Open findings（未解消）", out)
        self.assertIn("F-307-02", out)
        self.assertIn("harm_detail:", out)
        # 端末装飾・対話前提の文言を混ぜない。
        self.assertNotIn("\x1b[", out)
        for interactive in ("続けますか", "y/n", "[Y/n]"):
            self.assertNotIn(interactive, out)

    def test_missing_karte_is_still_not_found(self):
        code, _out, err = self._run(cli.cmd_render, issue="999")
        self.assertEqual(code, cli.EXIT_NOT_FOUND)
        self.assertIn("未検出", err)


# --- K-15: status をフックから実行できるようにする -----------------------------


class TestStatusForInjection(KarteTestCase):
    """K-15: PostToolUse フックが ``pr-reviewer`` 呼び出し完了直後に実行し注入する本文。"""

    def test_issue_is_filled_from_active_pointer(self):
        self._ingest(1, ("new", HARMFUL))
        code, out, err = self._run(cli.cmd_status, issue=None, json=False)
        self.assertEqual(code, cli.EXIT_OK, err)
        self.assertIn("issue-307", out)
        self.assertIn("harmful-open", out)

    def test_json_also_honors_active_pointer(self):
        """``--json`` は挙動維持（機械可読用）だが --issue 省略は同じく補完される。"""
        self._ingest(1, ("new", HARMFUL))
        code, out, err = self._run(cli.cmd_status, issue=None, json=True)
        self.assertEqual(code, cli.EXIT_OK, err)
        self.assertEqual(json.loads(out)["issue"], 307)

    def test_missing_active_pointer_is_fail_closed(self):
        code, _out, err = self._run(cli.cmd_status, issue=None, json=False)
        self.assertEqual(code, cli.EXIT_ERROR)
        self.assertIn("進行ポインタ", err)

    def test_broken_active_pointer_is_fail_closed(self):
        self._ingest(1, ("new", HARMFUL))
        self._active_path().write_text("not json at all", encoding="utf-8")
        code, _out, err = self._run(cli.cmd_status, issue=None, json=False)
        self.assertEqual(code, cli.EXIT_ERROR)
        self.assertIn("進行ポインタ", err)

    def test_output_is_self_contained_for_harmful_open(self):
        self._ingest(1, ("new", HARMFUL), ("new", COSMETIC))
        self._append(
            finding_ids=["F-307-01"], root_cause="attrs-overwrite",
            targets=["pkg/forms.py::build_attrs"],
        )
        code, out, err = self._run(cli.cmd_status, json=False)
        self.assertEqual(code, cli.EXIT_OK, err)

        # 何の本文か・どこから来たか（前後の文脈に依存しない）。
        self.assertIn("Issue #307", out)
        self.assertIn("issue-307.md", out)
        # verdict（実害あり残存／全件実害なし／無進捗のいずれか）。
        self.assertIn("verdict: harmful-open（実害あり残存）", out)
        # 残存 finding と harm 判定。
        self.assertIn("## 残存 finding（未解消・harm 判定つき）", out)
        self.assertIn("F-307-01 [harm=real]", out)
        self.assertIn("F-307-02 [harm=none]", out)
        # エスカレーション条件のどれに該当するか（この時点では該当しない）。
        self.assertIn("escalate: no（無進捗・飽和したアプローチのいずれにも該当しない）", out)
        # 端末装飾・対話前提の文言を混ぜない。
        self.assertNotIn("\x1b[", out)
        for interactive in ("続けますか", "y/n", "[Y/n]"):
            self.assertNotIn(interactive, out)

    def test_escalation_reason_is_explicit_when_stalled(self):
        self._ingest(1, ("new", HARMFUL))
        self._ingest(2, ("F-307-01", HARMFUL))
        self._ingest(3, ("F-307-01", HARMFUL))
        code, out, err = self._run(cli.cmd_status, json=False)
        self.assertEqual(code, cli.EXIT_OK, err)
        self.assertIn("escalate: yes（理由: 無進捗（F-307-01））", out)

    def test_missing_karte_is_still_not_found(self):
        code, _out, err = self._run(cli.cmd_status, issue="999", json=False)
        self.assertEqual(code, cli.EXIT_NOT_FOUND)
        self.assertIn("未検出", err)


# --- K-07: 正規化の保持文字クラス ----------------------------------------------


class TestNormalizeTextCoversAllScripts(unittest.TestCase):
    """K-07: 文字クラスを**列挙しない**（列挙すると漏れた文字体系で fail-open する）。

    是正前は ASCII 英数・かな・CJK 統合漢字だけを保持していたため、全角英数・ハングル・
    アクセント付きラテン・CJK 拡張漢字は空白へ畳まれ、要約がそれらだけで構成されると
    正規化結果が空になり :func:`model.is_same_finding` が常に False ＝**再発番の見逃し**。
    """

    SCRIPTS = {
        "全角英数": "ＡＢＣ１２３",
        "ハングル": "한글로 쓴 요약",
        "アクセント付きラテン": "café résumé naïve",
        "CJK拡張漢字": "𠀋𠀌𠀍𠀎",
        "キリル": "Проверка",
        "ギリシャ": "Παράδειγμα",
    }

    def test_letters_and_digits_survive_normalization(self):
        for name, text in self.SCRIPTS.items():
            with self.subTest(script=name):
                self.assertTrue(model.normalize_text(text))
                self.assertTrue(model.shingles(text))

    def test_reissued_id_is_detected_for_every_script(self):
        for name, text in self.SCRIPTS.items():
            with self.subTest(script=name):
                self.assertTrue(model.is_same_finding(text, "x.py::f", text, "y.py::g"))

    def test_reworded_restatement_is_detected_for_non_ascii_scripts(self):
        self.assertTrue(
            model.is_same_finding(
                "ＡＢＣ１２３ の初期化が漏れている", "pkg/a.py::init",
                "ＡＢＣ１２３ の初期化が漏れている（再掲）", "pkg/a.py::init",
            )
        )

    def test_symbols_and_punctuation_are_still_folded(self):
        self.assertEqual(model.normalize_text("a-b_c!!"), "a b c")
        self.assertEqual(model.normalize_text("  A  B  "), "a b")

    def test_compatibility_normalization_is_not_applied(self):
        """NFKC は掛けない（全角と半角を同一視すると別物を再発番と誤検出する）。"""
        self.assertNotEqual(model.normalize_text("ＡＢＣ"), model.normalize_text("ABC"))

    def test_existing_japanese_and_english_cases_do_not_regress(self):
        self.assertEqual(
            model.normalize_text("build_attrs が既存 attrs を破棄している"),
            "build attrs が既存 attrs を破棄している",
        )
        self.assertTrue(
            model.is_same_finding(
                "build_attrs が既存 attrs を破棄している", "a/b.py::build_attrs",
                "build_attrs が既存の attrs を破棄している（再掲）", "a/b.py::build_attrs",
            )
        )
        self.assertFalse(
            model.is_same_finding(
                "build_attrs が既存 attrs を破棄している", "a/b.py::build_attrs",
                "build_attrs の docstring が古い", "a/b.py::build_attrs",
            )
        )


# --- K-04: symlink 再検査の保証範囲（docstring の正直さ） -----------------------


class TestAtomicWriteDocstringStatesItsLimits(unittest.TestCase):
    """K-04: docstring が実装の保証を上回っていないこと（過大な保証表現を持たない）。

    ``Path.write_text`` / ``open("a")`` は symlink を追跡するため、``is_symlink()`` 検査と
    open の間に差し替えられれば追従する window が残る。「TOCTOU 対策」と書くと、原子的な
    保証があるかのように読める——実情（best-effort・厳密化は Issue #318）を書く。
    """

    def test_write_text_atomic_docstring_is_honest(self):
        doc = paths.write_text_atomic.__doc__
        # 「TOCTOU 対策」を**保証として**掲げない（是正前は「（TOCTOU 対策・…）」だった）。
        self.assertNotIn("（TOCTOU 対策", doc)
        self.assertIn("「TOCTOU 対策」と呼べる強さを持たない", doc)
        self.assertIn("best-effort", doc)
        self.assertIn("window", doc)
        self.assertIn("Issue #318", doc)
        self.assertIn("O_NOFOLLOW", doc)
        self.assertIn("_reverify_before_delete", doc)  # より厳密な比較対象を残す

    def test_append_text_docstring_is_honest(self):
        doc = paths.append_text.__doc__
        self.assertNotIn("（TOCTOU 対策", doc)
        self.assertIn("best-effort", doc)
        self.assertIn("window", doc)
        self.assertIn("Issue #318", doc)

    def test_reverification_still_rejects_symlinks(self):
        """保証範囲を狭めるのではなく、正直に書くだけ（検査自体は残す）。"""
        root = Path(tempfile.mkdtemp(prefix="karte-symlink-")).resolve()
        self.addCleanup(lambda: shutil.rmtree(root, ignore_errors=True))
        target = root / "real.md"
        target.write_text("x\n", encoding="utf-8")
        link = root / "link.md"
        try:
            link.symlink_to(target)
        except (OSError, NotImplementedError):  # pragma: no cover - symlink 不可環境
            self.skipTest("symlink を作れない環境")
        with self.assertRaises(paths.KartePathError):
            paths.write_text_atomic(link, "y\n")
        with self.assertRaises(paths.KartePathError):
            paths.append_text(link, "y\n")
        self.assertEqual(target.read_text(encoding="utf-8"), "x\n")


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
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as ctx:
                cli.main(["status", "--issue", "307", "--repo-root", str(self.root)])
        self.assertEqual(ctx.exception.code, 2)


# --- 公開 CLI 面（argv 経由） --------------------------------------------------


class TestCliOverArgv(KarteTestCase):
    """``python3 -m karte <verb>`` と同じ argv 経路で 5 verb ＋ ``close-attempt`` が動く。

    他のテストは ``cmd_*`` を Namespace 直呼びで検証しており argparse の結線
    （``--from``→``source`` / ``--finding-ids``→``finding_ids`` 等）を通らないため、
    公開 CLI 面はここで固定する。``--repo-root`` は公開フラグとして持たない設計なので、
    モジュール定数 ``_REPO_ROOT`` を一時リポジトリに差し替えて ``main()`` を呼ぶ。
    """

    def _main(self, *argv):
        buffer = io.StringIO()
        errors = io.StringIO()
        with mock.patch.object(cli, "_REPO_ROOT", self.root):
            with contextlib.redirect_stdout(buffer), contextlib.redirect_stderr(errors):
                code = cli.main(list(argv))
        return code, buffer.getvalue(), errors.getvalue()

    def test_five_verbs_over_argv(self):
        report = self._write_report("review-1.md", _report(("new", HARMFUL)))
        code, out, err = self._main(
            "ingest-review", "--issue", "307", "--round", "1", "--from", report
        )
        self.assertEqual(code, cli.EXIT_OK, err)
        self.assertIn("F-307-01", out)

        code, out, err = self._main("render", "--issue", "307")
        self.assertEqual(code, cli.EXIT_OK, err)
        self.assertIn("Prior attempts（DO NOT repeat these）", out)

        # --issue 省略＝進行ポインタ（active.json）から解決する。
        code, out, err = self._main(
            "append", "--finding-ids", "F-307-01", "--root-cause", "attrs-overwrite",
            "--change-kind", "logic", "--targets", "pkg/forms.py::build_attrs",
            "--diagnosis", "既存 attrs を作り直している",
        )
        self.assertEqual(code, cli.EXIT_OK, err)
        self.assertIn("Attempt 1", out)

        diff = self._write_report(
            "d1.patch",
            "--- a/pkg/forms.py\n+++ b/pkg/forms.py\n"
            "@@ -1 +1 @@ def build_attrs(self):\n-x\n+y\n",
        )
        code, out, err = self._main(
            "close-attempt", "--attempt", "1", "--outcome", "partial", "--diff-file", diff
        )
        self.assertEqual(code, cli.EXIT_OK, err)
        self.assertIn("pkg/forms.py::build_attrs", out)

        code, out, err = self._main("check", "--issue", "307", "--round", "1")
        self.assertEqual(code, cli.EXIT_OK, err)
        self.assertIn("網羅", out)

        code, out, err = self._main("status", "--issue", "307", "--json")
        self.assertEqual(code, cli.EXIT_OK, err)
        payload = json.loads(out)
        self.assertEqual(payload["verdict"], "harmful-open")
        self.assertEqual(payload["findings"][0]["attempts"][0]["results"][0]["outcome"], "partial")

    def test_saturation_exit_code_over_argv(self):
        report = self._write_report("review-1.md", _report(("new", HARMFUL)))
        self._main("ingest-review", "--issue", "307", "--round", "1", "--from", report)
        for _ in range(2):
            code, _out, err = self._main(
                "append", "--issue", "307", "--finding-ids", "F-307-01",
                "--root-cause", "attrs-overwrite", "--change-kind", "logic",
                "--targets", "pkg/forms.py::build_attrs",
            )
            self.assertEqual(code, cli.EXIT_OK, err)
        code, out, _err = self._main(
            "append", "--issue", "307", "--finding-ids", "F-307-01",
            "--root-cause", "attrs-overwrite", "--change-kind", "logic",
            "--targets", "pkg/forms.py::build_attrs",
        )
        self.assertEqual(code, cli.EXIT_SATURATED)
        self.assertIn("DIRECTIVE", out)

    def test_unknown_change_kind_is_a_usage_error(self):
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as ctx:
                cli.main([
                    "append", "--issue", "307", "--finding-ids", "F-307-01",
                    "--root-cause", "x", "--change-kind", "typo", "--targets", "a.py::f",
                ])
        self.assertEqual(ctx.exception.code, 2)


# --- 純関数（書式・類似・差分） ------------------------------------------------


class TestModel(unittest.TestCase):
    def test_roundtrip(self):
        karte = model.new_karte(307)
        karte.findings.append(
            model.Finding(id="F-307-01", harm="real", harm_detail="壊れる",
                          severity="major", locus=["a.py::f"], summary="要約",
                          evidence="a.py:1 を読んで確認",
                          expected="壊れない", recheck="再現手順を実行して直っていることを見る",
                          rounds=[1, 2])
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

    def test_same_finding_detects_reworded_restatement(self):
        """同一 locus での言い換え再掲は同一指摘（＝ID 再発番）と判定する。

        空白トークン化では日本語の助詞挿入（``既存`` → ``既存の``）で一致率が落ちるため、
        文字 n-gram で比較している（`model.shingles` の docstring 参照）。
        """
        self.assertTrue(
            model.is_same_finding(
                "build_attrs が既存 attrs を破棄している", "a/b.py::build_attrs",
                "build_attrs が既存の attrs を破棄している（再掲）", "a/b.py::build_attrs",
            )
        )

    def test_same_finding_does_not_merge_distinct_findings_at_same_locus(self):
        """同じ関数への**別の**指摘は同一視しない（正当な新規指摘を潰さない）。"""
        self.assertFalse(
            model.is_same_finding(
                "build_attrs が既存 attrs を破棄している", "a/b.py::build_attrs",
                "build_attrs の docstring が古い", "a/b.py::build_attrs",
            )
        )

    def test_same_finding_ignores_locus_when_summary_is_identical(self):
        self.assertTrue(model.is_same_finding("同じ要約", "x.py::f", "同じ要約", "y.py::g"))
        self.assertFalse(model.is_same_finding("要約A", "x.py::f", "要約B", "y.py::g"))

    def test_preamble_is_tolerated_only_for_review_reports(self):
        text = "# レビュー結果\n\n特になし\n\n### new\nharm: none\n"
        with self.assertRaises(model.KarteFormatError):
            model.parse_blocks(text)  # カルテ本体は 1 行でも解釈できなければ拒否
        blocks = model.parse_blocks(text, allow_preamble=True)
        self.assertEqual([block.title for block in blocks], ["new"])

    def test_stray_line_after_a_block_is_rejected_even_with_preamble(self):
        with self.assertRaises(model.KarteFormatError):
            model.parse_blocks("### new\nharm: none\n要約の折り返し\n", allow_preamble=True)

    def test_key_value_line_in_preamble_is_rejected_not_silently_dropped(self):
        """K-10: 最初の `###` より前でも `key: value` 行は自由文として黙って捨てない。

        `harm: real` のような行がブロック外（＝どの finding にも属さない）で書かれていたら、
        preamble 緩和の対象（自由文）ではなく書式違反として拒否する。
        """
        text = (
            "# レビュー結果\n\nharm: real\n\n### new\nharm: none\nharm_detail: d\n"
            "severity: minor\nlocus: x\nsummary: s\nevidence: v\nexpected: e\nrecheck: r\n"
        )
        with self.assertRaises(model.KarteFormatError) as ctx:
            model.parse_blocks(text, allow_preamble=True)
        self.assertIn("解釈できない行", str(ctx.exception))

    def test_ingest_review_rejects_report_with_key_value_preamble(self):
        """`parse_review` 経由（``ingest-review`` の実入力）でも同じく fail-close する。"""
        text = (
            "# レビュー結果\n\nharm: real\n\n### new\nharm: none\nharm_detail: d\n"
            "severity: minor\nlocus: x\nsummary: s\nevidence: v\nexpected: e\nrecheck: r\n"
        )
        with self.assertRaises(model.KarteFormatError):
            model.parse_review(text, 307)


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


# --- main worktree 導出（K-01） ------------------------------------------------


class TestMainWorktreeRoot(unittest.TestCase):
    """``paths.main_worktree_root``：linked worktree でもカルテ置き場を main へ収束させる。"""

    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="karte-mainwt-")).resolve()
        self.addCleanup(lambda: shutil.rmtree(self.root, ignore_errors=True))
        (self.root / "tmp").mkdir()
        (self.root / ".git").mkdir()

    def _make_linked_worktree(self, name="w"):
        worktree = self.root / ".worktrees" / name
        worktree.mkdir(parents=True)
        gitdir = self.root / ".git" / "worktrees" / name
        gitdir.mkdir(parents=True)
        (worktree / ".git").write_text(f"gitdir: {gitdir}\n", encoding="utf-8")
        return worktree, gitdir

    def test_main_worktree_itself_is_returned_as_is(self):
        self.assertEqual(paths.main_worktree_root(self.root), self.root)

    def test_linked_worktree_resolves_to_main_root_via_gitdir(self):
        worktree, _gitdir = self._make_linked_worktree()
        self.assertEqual(paths.main_worktree_root(worktree), self.root)

    def test_linked_worktree_prefers_commondir_file_when_present(self):
        worktree, gitdir = self._make_linked_worktree("w2")
        (gitdir / "commondir").write_text("../..\n", encoding="utf-8")
        self.assertEqual(paths.main_worktree_root(worktree), self.root)

    def test_directory_without_git_is_returned_as_is(self):
        bare = Path(tempfile.mkdtemp(prefix="karte-bare-")).resolve()
        self.addCleanup(lambda: shutil.rmtree(bare, ignore_errors=True))
        self.assertEqual(paths.main_worktree_root(bare), bare)

    def test_malformed_git_file_is_rejected(self):
        worktree = self.root / ".worktrees" / "bad"
        worktree.mkdir(parents=True)
        (worktree / ".git").write_text("not-a-gitdir-line\n", encoding="utf-8")
        with self.assertRaises(paths.KartePathError):
            paths.main_worktree_root(worktree)


class TestLinkedWorktreeConvergence(unittest.TestCase):
    """K-01: linked worktree で ``ingest-review`` した台帳を main worktree の ``render`` が読める。

    ``issue-implementer`` は isolated worktree で走る前提（Issue #307）。是正前は
    ``_REPO_ROOT`` が ``Path(__file__)`` 由来の候補パス（＝実行中の worktree）をそのまま
    使い、レビューア側の台帳（main worktree の ``tmp/_karte/``）と分裂していた。
    """

    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="karte-mainwt-")).resolve()
        self.addCleanup(lambda: shutil.rmtree(self.root, ignore_errors=True))
        (self.root / "tmp").mkdir()
        (self.root / ".git").mkdir()
        self.worktree = self.root / ".worktrees" / "w"
        self.worktree.mkdir(parents=True)
        gitdir = self.root / ".git" / "worktrees" / "w"
        gitdir.mkdir(parents=True)
        (self.worktree / ".git").write_text(f"gitdir: {gitdir}\n", encoding="utf-8")

    def _run_from(self, cwd_root, func, **kwargs):
        """``cwd_root`` を起点に ``_REPO_ROOT`` を導出し、公開フラグ無しで ``cmd_*`` を呼ぶ。

        ``--repo-root`` は公開 CLI フラグではないため、実運用と同じく ``args`` に
        ``repo_root`` を持たせず、``_REPO_ROOT``（モジュール既定値）だけを差し替える。
        """
        resolved = paths.main_worktree_root(cwd_root)
        buffer = io.StringIO()
        errors = io.StringIO()
        ns = argparse.Namespace(issue="307", **kwargs)
        with mock.patch.object(cli, "_REPO_ROOT", resolved):
            with contextlib.redirect_stdout(buffer), contextlib.redirect_stderr(errors):
                code = func(ns)
        return code, buffer.getvalue(), errors.getvalue()

    def test_ingest_from_worktree_is_visible_to_render_from_main(self):
        report = self.root / "tmp" / "review-1.md"
        report.write_text(
            "### new\nharm: real\nharm_detail: d\nseverity: major\nlocus: x\n"
            "summary: s\nevidence: v\nexpected: e\nrecheck: r\n",
            encoding="utf-8",
        )
        code, out, err = self._run_from(
            self.worktree, cli.cmd_ingest_review, round="1", source=str(report)
        )
        self.assertEqual(code, cli.EXIT_OK, err)
        self.assertIn("F-307-01", out)

        code, out, err = self._run_from(self.root, cli.cmd_render)
        self.assertEqual(code, cli.EXIT_OK, err)
        self.assertIn("F-307-01", out)

        # worktree 配下には一切カルテ置き場が作られない（分裂の再発防止）。
        self.assertFalse((self.worktree / "tmp").exists())


if __name__ == "__main__":
    unittest.main()
