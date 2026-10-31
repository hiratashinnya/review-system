"""karte ingest-reviewer / activate / decide（Issue #375）。実 tmp ディレクトリで検証する。"""

import argparse
import ast
import contextlib
import io
import tempfile
import shutil
import unittest
from pathlib import Path
from unittest import mock

from karte import cli, handoff_path, owner_decision, paths, reviewer_cli, scope_ledger, verb_support
from karte.errors import KarteUsageError
from karte.path_errors import KartePathError

FINDING = {
    "harm": "real",
    "harm_detail": "必須属性が消えて入力検証が素通りする",
    "severity": "major",
    "scope": "in",
    "evidence": "a/b.py:12 を読み、attrs を辞書リテラルで作り直しているのを確認",
    "locus": "a/b.py::build_attrs",
    "summary": "build_attrs が既存 attrs を破棄している",
    "expected": "既存 attrs を保ったまま追加分だけマージする",
    "recheck": "required 付きフィールドを描画し required が残ることを確認する",
}


def _report(title="new", **overrides):
    fields = {**FINDING, **overrides}
    return "\n".join([f"### {title}"] + [f"{k}: {v}" for k, v in fields.items()]) + "\n"


class ReviewerIngestCase(unittest.TestCase):
    issue = 375

    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="karte-rv-")).resolve()
        self.addCleanup(lambda: shutil.rmtree(self.root, ignore_errors=True))
        (self.root / "tmp" / "_handoff").mkdir(parents=True)

    def _run(self, func, **kwargs):
        params = {"repo_root": str(self.root), "issue": None, "round": None, **kwargs}
        args = argparse.Namespace(**params)
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = func(args)
        return code, out.getvalue(), err.getvalue()

    def _handoff(self, text, name="pr-reviewer--r1.md"):
        path = self.root / "tmp" / "_handoff" / name
        path.write_text(text, encoding="utf-8")
        return str(path)

    def _activate(self):
        return self._run(reviewer_cli.cmd_activate, issue=str(self.issue))

    def _ingest(self, text, name="pr-reviewer--r1.md"):
        return self._run(reviewer_cli.cmd_ingest_reviewer, source=self._handoff(text, name))

    def _karte(self):
        path = paths.karte_path(self.issue, self.root)
        return cli.model.parse(paths.read_text(path))

    def _decide(self, **kwargs):
        base = dict(
            finding=f"F-{self.issue}-01", disposition=None, deferred_to=None,
            waived_by=None, waived_reason=None, scope=None, issue=str(self.issue),
        )
        base.update(kwargs)
        return self._run(reviewer_cli.cmd_decide, **base)


class TestIngestReviewer(ReviewerIngestCase):
    def test_requires_active_pointer(self):
        code, _, err = self._ingest(_report())
        self.assertEqual(cli.EXIT_ERROR, code)
        self.assertIn("進行ポインタ", err)

    def test_first_round_after_activate_records_scope_original(self):
        self.assertEqual(cli.EXIT_OK, self._activate()[0])
        code, _, _ = self._ingest(_report(scope="out"))
        self.assertEqual(cli.EXIT_OK, code)
        finding = self._karte().finding(f"F-{self.issue}-01")
        self.assertEqual("out", finding.scope)
        self.assertEqual({finding.id: "out"}, scope_ledger.latest_declared(self.issue, self.root))

    def test_owner_only_keys_in_report_are_rejected_and_nothing_written(self):
        self._activate()
        text = _report(disposition="waived", waived_by="owner", waived_reason="自己免除")
        code, _, err = self._ingest(text)
        self.assertEqual(cli.EXIT_ERROR, code)
        self.assertIn("オーナー専権", err)
        self.assertFalse(paths.karte_path(self.issue, self.root).exists())

    def test_owner_decision_and_scope_override_survive_next_reviewer_round(self):
        self._activate()
        self._ingest(_report(scope="in"))
        self.assertEqual(cli.EXIT_OK, self._decide(disposition="deferred", deferred_to="#900", scope="out")[0])
        code, out, _ = self._ingest(
            _report(f"F-{self.issue}-01", scope="in", summary="build_attrs が既存 attrs を破棄している"),
            "pr-reviewer--r2.md",
        )
        self.assertEqual(cli.EXIT_OK, code)
        finding = self._karte().finding(f"F-{self.issue}-01")
        self.assertEqual(("deferred", "#900", "out"), (finding.disposition, finding.deferred_to, finding.scope))
        self.assertIn(f"F-{self.issue}-01", out)  # 覆しが取り込み出力に出る
        self.assertEqual("in", scope_ledger.latest_declared(self.issue, self.root)[finding.id])

    def test_explicit_issue_or_round_is_not_accepted_by_the_parser(self):
        parser = cli.build_parser((reviewer_cli.register,))
        for extra in (["--issue", "1"], ["--round", "1"]):
            with self.assertRaises(SystemExit), contextlib.redirect_stderr(io.StringIO()):
                parser.parse_args(["ingest-reviewer", "--from", "x", *extra])

    def test_source_outside_handoff_pattern_is_rejected(self):
        self._activate()
        for name in ("review.md", "pr-reviewer--x.txt"):
            code, _, err = self._ingest(_report(), name)
            self.assertEqual(cli.EXIT_ERROR, code, name)

    def test_decide_waived_requires_owner_and_reason(self):
        self._activate()
        self._ingest(_report())
        code, _, err = self._decide(disposition="waived")
        self.assertEqual(cli.EXIT_ERROR, code)
        self.assertIn("waived_by", err)


class TestHandoffPath(ReviewerIngestCase):
    def test_accepts_only_exact_handoff_pattern(self):
        good = self.root / "tmp" / "_handoff" / "pr-reviewer--k1.md"
        self.assertEqual(good, handoff_path.resolve_reviewer_handoff(good, self.root))
        bad = [
            "tmp/_handoff/other--k1.md", "tmp/_handoff/sub/pr-reviewer--k1.md",
            "tmp/_handoff/pr-reviewer--k1.md.sh", "tmp/_handoff/../_karte/pr-reviewer--k1.md",
            "tmp/pr-reviewer--k1.md", "/etc/pr-reviewer--k1.md", "tmp/_handoff/pr-reviewer--.md",
        ]
        for candidate in bad:
            with self.assertRaises(KartePathError, msg=candidate):
                handoff_path.resolve_reviewer_handoff(candidate, self.root)

    def test_symlinked_handoff_file_is_rejected(self):
        target = self.root / "tmp" / "elsewhere.md"
        target.write_text("x", encoding="utf-8")
        link = self.root / "tmp" / "_handoff" / "pr-reviewer--link.md"
        link.symlink_to(target)
        with self.assertRaises(KartePathError):
            handoff_path.resolve_reviewer_handoff(link, self.root)


class TestIngestReviewerHardening(ReviewerIngestCase):
    """PR #697 レビュー指摘（U1〜U6）の回帰テスト。"""

    def _main_context_ingest(self, text):
        path = self.root / "tmp" / "review-main.md"
        path.write_text(text, encoding="utf-8")
        return self._run(cli.cmd_ingest_review, issue=str(self.issue), round="9", source=str(path))

    def _declared_path(self):
        return paths.karte_dir(self.root) / f"issue-{self.issue}.declared-scope.jsonl"

    def _pointer(self, text):
        paths.active_path(self.root, create_dir=True).write_text(text, encoding="utf-8")

    def test_u1_main_context_ingest_review_is_refused_once_reviewer_ingest_exists(self):
        self._activate()
        self._ingest(_report())
        self._decide(disposition="deferred", deferred_to="#900")
        before = paths.karte_path(self.issue, self.root).read_text(encoding="utf-8")
        code, _, err = self._main_context_ingest(_report(f"F-{self.issue}-01"))
        self.assertEqual(cli.EXIT_ERROR, code)
        self.assertIn("ingest-reviewer", err)
        self.assertEqual(before, paths.karte_path(self.issue, self.root).read_text(encoding="utf-8"))

    def test_u1_main_context_ingest_review_still_works_without_reviewer_ingest(self):
        self.assertEqual(cli.EXIT_OK, self._main_context_ingest(_report())[0])

    def test_u2_corrupt_declared_scope_file_fails_closed_without_traceback(self):
        self._activate()
        self._ingest(_report())
        for corrupt in ("{not json\n", '{"round": 1, "id": "F-375-01"}\n', "[1, 2]\n"):
            with self.subTest(corrupt=corrupt):
                self._declared_path().write_text(corrupt, encoding="utf-8")
                code, _, err = self._ingest(_report(f"F-{self.issue}-01"), "pr-reviewer--r2.md")
                self.assertEqual(cli.EXIT_ERROR, code)
                self.assertIn("壊れている", err)

    def test_u2_and_u4_broken_pointer_round_fails_closed(self):
        self._activate()
        for text in ('{"issue": 375, "round": "x"}\n', '{"issue": 375}\n', '{"issue": 375, "round": -1}\n'):
            with self.subTest(pointer=text):
                self._pointer(text)
                code, _, err = self._ingest(_report())
                self.assertEqual(cli.EXIT_ERROR, code)
                self.assertIn("round", err)
        self.assertFalse(paths.karte_path(self.issue, self.root).exists())

    def test_u4_pointer_issue_mismatch_is_refused(self):
        self._pointer('{"issue": 1, "round": 0}\n')
        with self.assertRaises(KarteUsageError):
            verb_support.next_round(self.root, self.issue)

    def test_u3_retry_after_failed_ledger_write_does_not_mistake_new_scope_for_owner_override(self):
        self._activate()
        self._ingest(_report(scope="in"))
        report = _report(f"F-{self.issue}-01", scope="out")
        with mock.patch.object(paths, "write_text_atomic", side_effect=OSError("disk full")):
            self.assertEqual(cli.EXIT_ERROR, self._ingest(report, "pr-reviewer--r2.md")[0])
        self.assertEqual("in", self._karte().finding(f"F-{self.issue}-01").scope)
        self.assertEqual(cli.EXIT_OK, self._ingest(report, "pr-reviewer--r2.md")[0])
        self.assertEqual("out", self._karte().finding(f"F-{self.issue}-01").scope)

    def test_u5_reviewer_verbs_do_not_import_from_cli(self):
        for module in (reviewer_cli, owner_decision, verb_support):
            tree = ast.parse(Path(module.__file__).read_text(encoding="utf-8"))
            imported = [n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)]
            self.assertNotIn("cli", imported, module.__name__)

    def test_u6_agent_docs_tell_the_reviewer_to_write_an_absolute_main_checkout_path(self):
        root = Path(__file__).resolve().parents[2]
        for rel in (".claude/agents/pr-reviewer.md", ".ai/agents/pr-reviewer.md"):
            self.assertIn("主チェックアウトの絶対パス", (root / rel).read_text(encoding="utf-8"), rel)


if __name__ == "__main__":
    unittest.main()
