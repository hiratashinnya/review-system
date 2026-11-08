"""karte ingest-reviewer / activate / decide（Issue #375）。実 tmp ディレクトリで検証する。"""

import argparse
import ast
import contextlib
import io
import json
import tempfile
import shutil
import unittest
from pathlib import Path
from unittest import mock

from karte import cli, handoff_path, karte_rounds, owner_cli, owner_decision, paths, pointer_completion, reviewer_cli, reviewer_policy, scope_ledger, scope_records, verb_boundary
from karte.errors import KarteUsageError
from karte.int_args import parse_int
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
        return self._run(owner_cli.cmd_activate, issue=str(self.issue))

    def _next_round(self):
        """進行ポインタの次ラウンド（ポインタが読めなければ 1）。"""
        try:
            return parse_int(json.loads(paths.active_path(self.root).read_text(encoding="utf-8"))["round"], "round", minimum=0) + 1
        except (OSError, ValueError, KeyError, TypeError, KartePathError, KarteUsageError):  # KarteMissing も KartePathError
            return 1

    def _ingest_raw(self, text, name="pr-reviewer--r1.md"):
        return self._run(reviewer_cli.cmd_ingest_reviewer, source=self._handoff(text, name))

    def _ingest(self, text, name="pr-reviewer--r1.md"):
        """取り込み先と一致するヘッダ（issue / round）を付けて取り込む。"""
        header = f"<!-- handoff issue={self.issue} round={self._next_round()} -->\n\n"
        return self._ingest_raw(header + text, name)

    def _karte(self):
        path = paths.karte_path(self.issue, self.root)
        return cli.model.parse(paths.read_text(path))

    def _finding(self, finding_id):
        finding = self._karte().finding(finding_id)
        assert finding is not None
        return finding

    def _declared_scopes(self):
        latest = {}
        for _line, (_round, finding_id, scope, by) in scope_records.read_records(self.issue, self.root):
            if not by:
                latest[finding_id] = scope
        return latest

    def _decide(self, **kwargs):
        base = dict(
            finding=f"F-{self.issue}-01", disposition=None, deferred_to=None,
            waived_by=None, waived_reason=None, scope=None, issue=str(self.issue),
        )
        base.update(kwargs)
        return self._run(owner_cli.cmd_decide, **base)


class TestIngestReviewer(ReviewerIngestCase):
    def test_requires_active_pointer(self):
        code, _, err = self._ingest(_report())
        self.assertEqual(cli.EXIT_ERROR, code)
        self.assertIn("進行ポインタ", err)

    def test_first_round_after_activate_records_scope_original(self):
        self.assertEqual(cli.EXIT_OK, self._activate()[0])
        code, _, _ = self._ingest(_report(scope="out"))
        self.assertEqual(cli.EXIT_OK, code)
        finding = self._finding(f"F-{self.issue}-01")
        self.assertEqual("out", finding.scope)
        self.assertEqual({finding.id: "out"}, self._declared_scopes())

    def test_owner_only_keys_are_ignored_with_warnings(self):
        self._activate()
        self.assertEqual(cli.EXIT_OK, self._ingest(_report())[0])
        self.assertEqual(cli.EXIT_OK, self._decide(disposition="deferred", deferred_to="#9")[0])
        for key in ("disposition", "deferred_to", "waived_by", "waived_reason"):
            for value in ("", "unexpected"):
                with self.subTest(key=key, value=value):
                    code, out, err = self._ingest(_report(f"F-{self.issue}-01", **{key: value}))
                    self.assertEqual(cli.EXIT_OK, code, err)
                    finding = self._finding(f"F-{self.issue}-01")
                    self.assertEqual(("deferred", "#9", "", ""),
                                     (finding.disposition, finding.deferred_to, finding.waived_by, finding.waived_reason))
                    warning = f"警告: 13 行目: オーナー専権の {key} を無視"
                    self.assertEqual(warning + "\n", err)
                    self.assertEqual([
                        f"=== ingest-review: issue-{self.issue} round {self._next_round() - 1} ===",
                        "  取り込み: 1 件（新規 0 / 再掲 1）",
                        f"  未解消: F-{self.issue}-01",
                        f"  カルテ: {paths.karte_path(self.issue, self.root)}",
                        "  " + warning,
                    ], out.splitlines())

    def test_owner_decision_and_scope_override_survive_next_reviewer_round(self):
        self._activate()
        self._ingest(_report(scope="in"))
        self.assertEqual(cli.EXIT_OK, self._decide(disposition="deferred", deferred_to="#900", scope="out")[0])
        code, out, _ = self._ingest(
            _report(f"F-{self.issue}-01", scope="in", summary="build_attrs が既存 attrs を破棄している"),
            "pr-reviewer--r2.md",
        )
        self.assertEqual(cli.EXIT_OK, code)
        finding = self._finding(f"F-{self.issue}-01")
        self.assertEqual(("deferred", "#900", "out"), (finding.disposition, finding.deferred_to, finding.scope))
        kept_line = f"  オーナーが確定した scope を保持（レビューア申告と台帳が不一致）: F-{self.issue}-01"
        self.assertEqual([kept_line], [line for line in out.splitlines() if "オーナーが確定した scope を保持" in line])
        self.assertEqual("in", self._declared_scopes()[finding.id])

    def test_explicit_issue_is_rejected_but_round_is_accepted_by_the_parser(self):
        parser = cli.build_parser((reviewer_cli.register,))
        for extra in (["--issue", "1"],):
            with self.assertRaises(SystemExit), contextlib.redirect_stderr(io.StringIO()):
                parser.parse_args(["ingest-reviewer", "--from", "x", *extra])
        parsed = parser.parse_args(["ingest-reviewer", "--from", "x", "--round", "1"])
        self.assertEqual("1", parsed.round)
        reviewer_help = parser._subparsers._group_actions[0].choices["ingest-reviewer"].format_help()
        self.assertIn("通常は省略", reviewer_help)
        self.assertIn("台帳最新 round と同じ値", reviewer_help)

    def test_reviewer_same_round_retry_requires_explicit_round(self):
        self._activate()
        self.assertEqual(cli.EXIT_OK, self._ingest(_report(scope="in"))[0])
        report = f"<!-- handoff issue={self.issue} round=1 -->\n\n" + _report(
            f"F-{self.issue}-01", scope="out"
        )
        paths.active_path(self.root, create_dir=True).write_text(
            json.dumps({"issue": self.issue, "round": 0}), encoding="utf-8"
        )
        code, _, err = self._ingest_raw(report, "pr-reviewer--retry.md")
        self.assertEqual(cli.EXIT_ERROR, code)
        self.assertIn("round は単調増加", err)
        code, _, err = self._run(
            reviewer_cli.cmd_ingest_reviewer,
            source=self._handoff(report, "pr-reviewer--retry.md"), round="1",
        )
        self.assertEqual(cli.EXIT_OK, code, err)
        self.assertEqual("out", self._finding(f"F-{self.issue}-01").scope)

    def test_explicit_reviewer_round_must_match_latest_round(self):
        self._activate()
        self.assertEqual(cli.EXIT_OK, self._ingest(_report())[0])
        self.assertEqual(cli.EXIT_OK, self._ingest(_report(f"F-{self.issue}-01"), "pr-reviewer--r2.md")[0])
        karte_path = paths.karte_path(self.issue, self.root)
        before = karte_path.read_bytes()

        for requested, pointer_round in ((1, 1), (3, 2)):
            with self.subTest(requested=requested):
                paths.active_path(self.root, create_dir=True).write_text(
                    json.dumps({"issue": self.issue, "round": pointer_round}), encoding="utf-8"
                )
                report = f"<!-- handoff issue={self.issue} round={requested} -->\n\n" + _report(
                    f"F-{self.issue}-01", scope="out"
                )
                code, _, err = self._run(
                    reviewer_cli.cmd_ingest_reviewer,
                    source=self._handoff(report, f"pr-reviewer--round-{requested}.md"),
                    round=str(requested),
                )
                self.assertEqual(cli.EXIT_ERROR, code)
                self.assertIn("最新ラウンドと同じ値", err)
                self.assertEqual(before, karte_path.read_bytes())

    def test_source_outside_handoff_pattern_is_rejected(self):
        self._activate()
        for name in ("review.md", "pr-reviewer--x.txt"):
            code, _, err = self._ingest(_report(), name)
            self.assertEqual(cli.EXIT_ERROR, code, name)
            self.assertIn("ファイル名", err, name)

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
            "docs/_handoff/pr-reviewer--k.md", "tmp/x/_handoff/pr-reviewer--k.md",
            "tmp/_handoff/pr-reviewer--a b.md", "tmp/_handoff/pr-reviewer--a;b.md",
            "tmp/_handoff/pr-reviewer--a$(x).md", "tmp/_handoff/pr-reviewer--日本.md",
            "tmp/_handoff/pr-reviewer---a.md", "tmp/_handoff/pr-reviewer--.a.md",
        ]
        for candidate in bad:
            with self.assertRaises(KartePathError, msg=candidate) as caught:
                handoff_path.resolve_reviewer_handoff(candidate, self.root)
            self.assertTrue(any(fragment in str(caught.exception) for fragment in
                                ("直下ではない", "ファイル名", "..", "外")), candidate)

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

    def test_decide_scope_preserves_all_declared_records_and_rejects_corruption(self):
        self._activate()
        self.assertEqual(cli.EXIT_OK, self._ingest(_report())[0])
        self.assertEqual(cli.EXIT_OK, self._ingest(_report(f"F-{self.issue}-01", scope="out"))[0])
        path = self._declared_path()
        before = path.read_text(encoding="utf-8").splitlines()
        self.assertEqual(cli.EXIT_OK, self._decide(scope="in")[0])
        self.assertEqual(before, path.read_text(encoding="utf-8").splitlines()[:-1])
        path.write_text(path.read_text(encoding="utf-8") + "{broken\n", encoding="utf-8")
        code, _, err = self._decide(scope="out")
        self.assertEqual(cli.EXIT_ERROR, code)
        self.assertIn("壊れている", err)

    def test_latest_owner_and_reviewer_scope_wins(self):
        self._activate()
        self.assertEqual(cli.EXIT_OK, self._ingest(_report(scope="in"))[0])
        self.assertEqual(cli.EXIT_OK, self._ingest(_report(f"F-{self.issue}-01", scope="out"))[0])
        self.assertEqual("out", self._declared_scopes()[f"F-{self.issue}-01"])
        self.assertEqual(cli.EXIT_OK, self._decide(scope="out")[0])
        self.assertEqual(cli.EXIT_OK, self._decide(scope="in")[0])
        self.assertEqual("in", scope_ledger.owner_scopes(self.issue, self.root)[f"F-{self.issue}-01"])
        self.assertEqual("in", self._finding(f"F-{self.issue}-01").scope)

    def test_disposition_kept_by_both_protected_ingest_routes(self):
        self._activate()
        self.assertEqual(cli.EXIT_OK, self._ingest(_report())[0])
        self.assertEqual(cli.EXIT_OK, self._decide(disposition="deferred", deferred_to="#9")[0])
        report = _report(f"F-{self.issue}-01")
        self.assertEqual(cli.EXIT_OK, self._ingest(report)[0])
        self.assertEqual(cli.EXIT_OK, self._main_context_ingest_round(
            2, _report(scope="out", summary="別の指摘", locus="b.py::other")
        )[0])
        finding = self._finding(f"F-{self.issue}-01")
        self.assertEqual(("deferred", "#9", "", ""),
                         (finding.disposition, finding.deferred_to, finding.waived_by, finding.waived_reason))
        self.assertEqual([1, 2], finding.rounds)
        self.assertEqual(cli.EXIT_OK, self._ingest(report)[0])
        self.assertEqual([1, 2, 3], self._finding(f"F-{self.issue}-01").rounds)

    def test_protected_main_context_rejects_every_existing_id_without_writes(self):
        self._activate()
        self.assertEqual(cli.EXIT_OK, self._ingest(
            _report() + "\n" + _report(summary="二つ目", locus="z/module.py::unique")
        )[0])
        self.assertEqual(cli.EXIT_OK, self._decide(disposition="deferred", deferred_to="#9", scope="out")[0])
        files = [paths.karte_path(self.issue, self.root), self._declared_path(), paths.active_path(self.root)]
        before = [path.read_bytes() for path in files]
        code, out, err = self._main_context_ingest_round(
            2, _report(f"F-{self.issue}-01", scope="in") + "\n" +
            _report(f"F-{self.issue}-02", summary="二つ目の既存 finding", locus="b.py::other")
        )
        self.assertEqual(cli.EXIT_ERROR, code)
        self.assertEqual("", out)
        self.assertIn(
            "保護モードの ingest-review は新規 finding の追記専用。既存 finding の変更は "
            "decide（オーナー決定）か、レビューア本人の ingest-reviewer で行う",
            err,
        )
        self.assertIn(f"F-{self.issue}-01", err)
        self.assertIn(f"F-{self.issue}-02", err)
        self.assertEqual(before, [path.read_bytes() for path in files])

    def test_protected_main_context_rejects_mixed_new_and_existing_ids_without_writes(self):
        self._activate()
        self.assertEqual(cli.EXIT_OK, self._ingest(_report())[0])
        self.assertEqual(cli.EXIT_OK, self._decide(scope="out")[0])
        files = [paths.karte_path(self.issue, self.root), self._declared_path(), paths.active_path(self.root)]
        before = [path.read_bytes() for path in files]
        mixed = _report(f"F-{self.issue}-01", scope="in") + "\n" + _report(
            "new", summary="新規 finding", locus="new.py::new"
        )
        code, out, err = self._main_context_ingest_round(2, mixed)
        self.assertEqual(cli.EXIT_ERROR, code)
        self.assertEqual("", out)
        self.assertIn("追記専用", err)
        self.assertIn(f"F-{self.issue}-01", err)
        self.assertEqual(before, [path.read_bytes() for path in files])

    def test_main_ingest_omitted_round_uses_latest_when_pointer_lags(self):
        self._activate()
        self.assertEqual(cli.EXIT_OK, self._ingest(_report())[0])
        self.assertEqual(cli.EXIT_OK, self._ingest(
            _report(f"F-{self.issue}-01"), "pr-reviewer--r2.md"
        )[0])
        paths.active_path(self.root, create_dir=True).write_text(
            json.dumps({"issue": self.issue, "round": 1}), encoding="utf-8"
        )
        report = self.root / "tmp" / "review-main-omitted-round.md"
        report.write_text(_report("new", summary="別件", locus="other.py::new"), encoding="utf-8")
        code, _out, err = self._run(
            cli.cmd_ingest_review, issue=None, round=None, source=str(report)
        )
        self.assertEqual(cli.EXIT_OK, code, err)
        self.assertEqual([2], self._finding(f"F-{self.issue}-02").rounds)
        active = json.loads(paths.active_path(self.root).read_text(encoding="utf-8"))
        self.assertEqual({"issue": self.issue, "round": 2}, active)

    def test_owner_scope_is_reapplied_to_findings_omitted_from_protected_review(self):
        self._activate()
        self.assertEqual(cli.EXIT_OK, self._ingest(_report(scope="in"))[0])
        finding_id = f"F-{self.issue}-01"
        scope_ledger.record_owner(self.issue, self.root, 1, finding_id, "out")

        report = _report("new", scope="in", summary="新規 finding", locus="new.py::new")
        code, _, err = self._ingest(report, "pr-reviewer--r2.md")
        self.assertEqual(cli.EXIT_OK, code, err)
        self.assertEqual("out", self._finding(finding_id).scope)

        ledger = paths.karte_path(self.issue, self.root)
        ledger_text = ledger.read_text(encoding="utf-8")
        self.assertIn("scope: out", ledger_text)
        ledger.write_text(ledger_text.replace("scope: out", "scope: in", 1), encoding="utf-8")
        self.assertEqual("in", self._finding(finding_id).scope)

        code, _, err = self._main_context_ingest_round(
            3, _report("new", scope="in", summary="別の新規 finding", locus="other.py::new")
        )
        self.assertEqual(cli.EXIT_OK, code, err)
        self.assertEqual("out", self._finding(finding_id).scope)

    def test_protected_main_context_accepts_new_ids_and_preserves_omitted_open_findings(self):
        self._activate()
        self.assertEqual(cli.EXIT_OK, self._ingest(_report())[0])
        self.assertEqual(cli.EXIT_OK, self._decide(disposition="deferred", deferred_to="#9")[0])
        before = self._finding(f"F-{self.issue}-01")
        code, _, err = self._main_context_ingest_round(
            2, _report(scope="out", summary="別件を追記", locus="b.py::other")
        )
        self.assertEqual(cli.EXIT_OK, code, err)
        self.assertEqual(before, self._finding(f"F-{self.issue}-01"))
        self.assertEqual("別件を追記", self._finding(f"F-{self.issue}-02").summary)

    def test_main_context_ignores_owner_keys_in_new_blocks_and_preserves_owner_ledger_values(self):
        self._activate()
        self.assertEqual(cli.EXIT_OK, self._ingest(_report())[0])
        self.assertEqual(cli.EXIT_OK, self._decide(disposition="deferred", deferred_to="#90")[0])
        first = _report(
            summary="新規の別指摘", locus="z/module.py::first",
            disposition="waived", deferred_to="#91", waived_by="owner", waived_reason="理由"
        )
        second = _report(
            summary="さらに別の新規指摘", locus="y/module.py::second",
            disposition="deferred", deferred_to="#92",
            waived_by="another owner", waived_reason="別理由",
        )
        code, out, err = self._main_context_ingest_round(2, first + "\n" + second)
        self.assertEqual(cli.EXIT_OK, code, err)
        warning_lines = [
            "警告: 11 行目: オーナー専権の disposition を無視",
            "警告: 12 行目: オーナー専権の deferred_to を無視",
            "警告: 13 行目: オーナー専権の waived_by を無視",
            "警告: 14 行目: オーナー専権の waived_reason を無視",
            "警告: 26 行目: オーナー専権の disposition を無視",
            "警告: 27 行目: オーナー専権の deferred_to を無視",
            "警告: 28 行目: オーナー専権の waived_by を無視",
            "警告: 29 行目: オーナー専権の waived_reason を無視",
            f"警告: 再掲されなかった未解消 finding を引き継ぎ: F-{self.issue}-01",
        ]
        self.assertEqual("".join(line + "\n" for line in warning_lines), err)
        self.assertEqual(warning_lines, [line.strip() for line in out.splitlines() if "警告:" in line])
        existing = self._finding(f"F-{self.issue}-01")
        self.assertEqual(("deferred", "#90"), (existing.disposition, existing.deferred_to))
        self.assertEqual(("", "", ""), (self._finding(f"F-{self.issue}-02").disposition,
                                          self._finding(f"F-{self.issue}-02").waived_by,
                                          self._finding(f"F-{self.issue}-02").waived_reason))
        self.assertIn(f"  警告: 11 行目: オーナー専権の disposition を無視", out)

    def test_owner_key_filter_preserves_malformed_line_number(self):
        report = "### new\ndisposition: deferred\nnot a valid report row\n" + _report().split("\n", 1)[1]
        filtered, warnings = reviewer_policy.ignore_owner_keys(report)
        self.assertEqual(["2 行目: オーナー専権の disposition を無視"], warnings)
        with self.assertRaises(cli.model.KarteFormatError) as caught:
            cli.model.parse_review(filtered, self.issue)
        self.assertIn("3 行目: 解釈できない行", str(caught.exception))

    def test_indented_owner_only_key_is_ignored_with_warning(self):
        report = _report().replace("scope: in", "  disposition: deferred\nscope: in")
        filtered, warnings = reviewer_policy.ignore_owner_keys(report)
        self.assertEqual(["5 行目: オーナー専権の disposition を無視"], warnings)
        self.assertNotIn("disposition:", filtered)
        self.assertEqual("in", cli.model.parse_review(filtered, self.issue)[0].scope)

    def test_owner_keys_after_headings_and_in_preamble_are_rejected(self):
        cases = (
            ("disposition: deferred\n" + _report(), 0),
            ("## Findings\ndisposition: deferred\n" + _report(), 0),
            ("### new\ndisposition: deferred\n# Title\nwaived_by: owner\n" + _report().split("\n", 1)[1], 1),
            ("### new\ndisposition: deferred\n## Other\nwaived_by: owner\n" + _report().split("\n", 1)[1], 1),
        )
        for report, expected_warnings in cases:
            with self.subTest(report=report):
                filtered, warnings = reviewer_policy.ignore_owner_keys(report)
                self.assertEqual(expected_warnings, len(warnings))
                with self.assertRaises(cli.model.KarteFormatError):
                    cli.model.parse_review(filtered, self.issue)

    def test_multiple_protected_warnings_cover_two_open_ids_and_two_new_block_keys(self):
        self._activate()
        seed = _report() + "\n" + _report(summary="二つ目", locus="z/module.py::unique")
        self.assertEqual(cli.EXIT_OK, self._ingest(seed)[0])
        first = _report(summary="新しい別件", locus="x/module.py::first", disposition="deferred")
        second = _report(summary="もう一つ別件", locus="y/module.py::second", deferred_to="#55")
        code, out, err = self._main_context_ingest_round(2, first + "\n" + second)
        self.assertEqual(cli.EXIT_OK, code, err)
        warning_lines = [
            "警告: 11 行目: オーナー専権の disposition を無視",
            "警告: 23 行目: オーナー専権の deferred_to を無視",
            f"警告: 再掲されなかった未解消 finding を引き継ぎ: F-{self.issue}-01, F-{self.issue}-02",
        ]
        self.assertEqual("".join(line + "\n" for line in warning_lines), err)
        self.assertEqual(
            [f"  {line}" for line in warning_lines],
            [line for line in out.splitlines() if line.startswith("  警告:")],
        )
        self.assertEqual("open", self._finding(f"F-{self.issue}-01").status)
        self.assertEqual("open", self._finding(f"F-{self.issue}-02").status)

    def test_decide_scope_marker_is_reapplied_after_ledger_write_failure(self):
        self._activate()
        self.assertEqual(cli.EXIT_OK, self._ingest(_report(scope="in"))[0])
        with mock.patch.object(owner_decision, "write_karte", side_effect=OSError("disk full")):
            code, _, err = self._decide(scope="out")
        self.assertEqual(cli.EXIT_ERROR, code)
        self.assertIn("印は保存済み。再度 decide か ingest で台帳へ反映される", err)
        finding_id = f"F-{self.issue}-01"
        self.assertEqual("in", self._finding(finding_id).scope)
        self.assertEqual({finding_id: "out"}, scope_ledger.owner_scopes(self.issue, self.root))
        code, out, err = self._ingest(_report(finding_id, scope="in"))
        self.assertEqual(cli.EXIT_OK, code, err)
        self.assertEqual("out", self._finding(finding_id).scope)
        kept_line = f"  オーナーが確定した scope を保持（レビューア申告と台帳が不一致）: {finding_id}"
        self.assertIn(kept_line, out.splitlines())

    def test_reviewer_carries_forward_finding_added_by_main_context(self):
        self._activate()
        self.assertEqual(cli.EXIT_OK, self._ingest(_report())[0])
        extra = _report(scope="out", summary="別の問題", locus="b.py::other")
        self.assertEqual(cli.EXIT_OK, self._main_context_ingest_round(1, extra)[0])
        before = self._finding(f"F-{self.issue}-02")
        code, out, err = self._ingest(_report(f"F-{self.issue}-01"))
        self.assertEqual(cli.EXIT_OK, code, err)
        self.assertEqual(before, self._finding(f"F-{self.issue}-02"))
        self.assertEqual("open", self._finding(f"F-{self.issue}-02").status)
        warning = f"警告: 再掲されなかった未解消 finding を引き継ぎ: F-{self.issue}-02"
        self.assertEqual(warning + "\n", err)
        self.assertEqual("  " + warning, out.splitlines()[-1])
        self.assertEqual({f"F-{self.issue}-01"}, set(self._declared_scopes()))

    def test_protected_round_cannot_move_backwards(self):
        self._activate()
        self.assertEqual(cli.EXIT_OK, self._ingest(_report())[0])
        self.assertEqual(cli.EXIT_OK, self._ingest(_report(f"F-{self.issue}-01"))[0])
        code, _, err = self._main_context_ingest_round(1, _report(f"F-{self.issue}-01"))
        self.assertEqual(cli.EXIT_ERROR, code)
        self.assertIn("round は単調増加", err)

    def test_unprotected_ingest_keeps_old_owner_fields_and_missing_open_rules(self):
        self.assertEqual(cli.EXIT_OK, self._main_context_ingest_round(1, _report())[0])
        report = _report(f"F-{self.issue}-01", disposition="deferred", deferred_to="#9")
        self.assertEqual(cli.EXIT_OK, self._main_context_ingest_round(2, report)[0])
        self.assertEqual(("deferred", "#9"), (self._finding(f"F-{self.issue}-01").disposition,
                                             self._finding(f"F-{self.issue}-01").deferred_to))
        code, _, err = self._main_context_ingest_round(3, _report(summary="別の問題", locus="b.py::other"))
        self.assertEqual(cli.EXIT_ERROR, code)
        self.assertIn("前ラウンドで未解消の finding が今回のレポートに再掲されていない", err)
        self.assertIn(f"F-{self.issue}-01", err)

    def test_activate_uses_maximum_round_across_findings(self):
        self.assertEqual(cli.EXIT_OK, self._main_context_ingest_round(1, _report())[0])
        text = _report(f"F-{self.issue}-01", status="resolved") + "\n" + _report(summary="別の問題", locus="b.py::other")
        self.assertEqual(cli.EXIT_OK, self._main_context_ingest_round(2, text)[0])
        self.assertEqual(2, karte_rounds.last_round(self._karte()))
        self.assertEqual(cli.EXIT_OK, self._activate()[0])
        pointer = json.loads(paths.active_path(self.root).read_text(encoding="utf-8"))
        self.assertEqual(2, pointer["round"])

    def test_handoff_header_must_be_a_complete_line_before_findings(self):
        self._activate()
        valid = f"<!-- handoff issue={self.issue} round=1 -->"
        for report in (_report() + "\n" + valid + "\n", valid + " junk\n\n" + _report()):
            with self.subTest(report=report):
                code, _, err = self._ingest_raw(report)
                self.assertEqual(cli.EXIT_ERROR, code)
                self.assertIn("ヘッダが無い", err)

    def test_main_context_ingest_keeps_open_findings_and_owner_decisions(self):
        self._activate()
        self._ingest(_report())
        self._decide(disposition="deferred", deferred_to="#900")
        before = self._finding(f"F-{self.issue}-01")
        code, out, err = self._main_context_ingest(_report(scope="out", summary="別の問題", locus="b.py::other"))
        self.assertEqual(cli.EXIT_OK, code, err)
        self.assertEqual(before, self._finding(f"F-{self.issue}-01"))
        self.assertEqual("open", self._finding(f"F-{self.issue}-01").status)
        warning = f"警告: 再掲されなかった未解消 finding を引き継ぎ: F-{self.issue}-01"
        self.assertEqual(warning + "\n", err)
        self.assertEqual([
            f"=== ingest-review: issue-{self.issue} round 9 ===",
            "  取り込み: 1 件（新規 1 / 再掲 0）",
            f"  新規採番: F-{self.issue}-02",
            f"  未解消: F-{self.issue}-01, F-{self.issue}-02",
            f"  うち scope: out（実害判定・verdict の免除にはならない）: F-{self.issue}-02",
            f"  実害あり・disposition 未決定（clean を妨げる。fix-here / deferred / waived を決める）: F-{self.issue}-02",
            f"  カルテ: {paths.karte_path(self.issue, self.root)}",
            "  " + warning,
        ], out.splitlines())
        self.assertEqual({f"F-{self.issue}-01"}, set(self._declared_scopes()))
        self.assertEqual("out", self._finding(f"F-{self.issue}-02").scope)

    def test_u1_main_context_ingest_review_still_works_without_reviewer_ingest(self):
        self.assertEqual(cli.EXIT_OK, self._main_context_ingest(_report())[0])

    def test_u2_corrupt_declared_scope_file_fails_closed_without_traceback(self):
        self._activate()
        self._ingest(_report())
        for corrupt in ("{not json\n", '{"round": 1, "id": "F-375-01"}\n', "[1, 2]\n",
                        '{"round": 1, "id": "F-375-01", "scope": "bad"}\n',
                        '{"round": 1, "id": "F-375-01", "scope": "in", "by": "bad"}\n',
                        '{"round": 1, "id": 42, "scope": "in"}\n'):
            with self.subTest(corrupt=corrupt):
                self._declared_path().write_text(corrupt, encoding="utf-8")
                code, _, err = self._ingest(_report(f"F-{self.issue}-01"), "pr-reviewer--r2.md")
                self.assertEqual(cli.EXIT_ERROR, code)
                self.assertIn("壊れている", err)

    def test_u2_and_u4_broken_pointer_round_fails_closed(self):
        self._activate()
        for text in (
            '{"issue": 375, "round": "x"}\n', '{"issue": 375}\n', '{"issue": 375, "round": -1}\n',
            '{"issue": 375, "round": "²"}\n', '{"issue": 375, "round": "٣"}\n',  # 非 ASCII 数字
        ):
            with self.subTest(pointer=text):
                self._pointer(text)
                code, _, err = self._ingest(_report())
                self.assertEqual(cli.EXIT_ERROR, code)
                self.assertIn("round", err)
        self.assertFalse(paths.karte_path(self.issue, self.root).exists())

    def test_u4_pointer_issue_mismatch_is_refused(self):
        self._pointer('{"issue": 1, "round": 0}\n')
        with self.assertRaises(KarteUsageError):
            pointer_completion.ingest_target(argparse.Namespace(issue=self.issue, round=None), self.root, pointer_minimum=0)

    def test_u3_retry_after_failed_sidefile_or_ledger_write(self):
        for failing in ("sidefile", "ledger"):
            with self.subTest(failing=failing):
                self.setUp()
                self._activate()
                self.assertEqual(cli.EXIT_OK, self._ingest(_report(scope="in"))[0])
                report = _report(f"F-{self.issue}-01", scope="out")
                before_ledger = paths.karte_path(self.issue, self.root).read_text(encoding="utf-8")
                before_side = self._declared_path().read_text(encoding="utf-8")
                original = paths.write_text_atomic

                def write(path, content):
                    target = self._declared_path() if failing == "sidefile" else paths.karte_path(self.issue, self.root)
                    if path == target:
                        raise OSError("disk full")
                    return original(path, content)

                with mock.patch.object(paths, "write_text_atomic", side_effect=write):
                    code, _, err = self._ingest(report, "pr-reviewer--r2.md")
                self.assertEqual(cli.EXIT_ERROR, code)
                self.assertIn("disk full", err)
                self.assertEqual(before_ledger, paths.karte_path(self.issue, self.root).read_text(encoding="utf-8"))
                side = self._declared_path().read_text(encoding="utf-8")
                self.assertEqual(failing == "ledger", side != before_side)
                self.assertEqual(cli.EXIT_OK, self._ingest(report, "pr-reviewer--r2.md")[0])
                self.assertEqual("out", self._finding(f"F-{self.issue}-01").scope)
                self.assertEqual(2, len(self._declared_path().read_text(encoding="utf-8").splitlines()))

    def test_r1_owner_scope_decided_on_a_finding_without_declared_record_is_kept(self):
        self.assertEqual(cli.EXIT_OK, self._main_context_ingest_round(1, _report(scope="in"))[0])
        self.assertEqual(cli.EXIT_OK, self._decide(scope="out")[0])
        code, out, _ = self._ingest(_report(f"F-{self.issue}-01", scope="in"), "pr-reviewer--r2.md")
        self.assertEqual(cli.EXIT_OK, code)
        self.assertEqual("out", self._finding(f"F-{self.issue}-01").scope)
        self.assertIn(
            f"  オーナーが確定した scope を保持（レビューア申告と台帳が不一致）: F-{self.issue}-01",
            out.splitlines(),
        )

    def test_r2_non_ascii_digit_pointer_round_is_a_refusal_not_a_traceback(self):
        self._pointer('{"issue": 375, "round": "²"}\n')
        with self.assertRaises(KarteUsageError):
            pointer_completion.ingest_target(argparse.Namespace(issue=self.issue, round=None), self.root, pointer_minimum=0)

    def test_r3_append_keeps_the_file_valid_and_newline_terminated(self):
        self._activate()
        self._ingest(_report())
        path = self._declared_path()
        path.write_text(path.read_text(encoding="utf-8").rstrip("\n"), encoding="utf-8")  # 末尾改行なし
        self.assertEqual(cli.EXIT_OK, self._ingest(_report(f"F-{self.issue}-01"), "pr-reviewer--r2.md")[0])
        text = path.read_text(encoding="utf-8")
        self.assertTrue(text.endswith("\n"))
        self.assertEqual(2, len(text.splitlines()))
        self.assertEqual({f"F-{self.issue}-01"}, set(self._declared_scopes()))

    def test_r3_corrupt_declared_scope_names_the_repair_and_the_repair_restores_service(self):
        self._activate()
        self._ingest(_report())
        path = self._declared_path()
        good = path.read_text(encoding="utf-8")
        path.write_text(good + '{"round": 2, "id": "F-375-01", "sco', encoding="utf-8")  # 途中切れの末尾行
        code, _, err = self._ingest(_report(f"F-{self.issue}-01"), "pr-reviewer--r2.md")
        self.assertEqual(cli.EXIT_ERROR, code)
        self.assertIn("--repair-declared-scope", err)
        out_code, out, _ = self._run(owner_cli.cmd_activate, issue=str(self.issue), repair_declared_scope=True)
        self.assertEqual(cli.EXIT_OK, out_code)
        self.assertIn("1 件", out)
        self.assertTrue(path.with_name(path.name + ".bak").is_file())
        self.assertEqual(good, path.read_text(encoding="utf-8"))
        self.assertEqual(cli.EXIT_OK, self._ingest(_report(f"F-{self.issue}-01"), "pr-reviewer--r2.md")[0])

    def test_r5_pointer_round_zero_is_only_derived_by_ingest_reviewer(self):
        """round 0（未取込）は ingest-reviewer だけが自動導出に使う。ingest-review の初回は従来どおり明示する。"""
        self._activate()
        path = self.root / "tmp" / "review-main.md"
        path.write_text(_report(), encoding="utf-8")
        code, _, _ = self._run(cli.cmd_ingest_review, issue=str(self.issue), round=None, source=str(path))
        self.assertEqual(cli.EXIT_ERROR, code)
        self.assertEqual(cli.EXIT_OK, self._main_context_ingest_round(1, _report())[0])
        self.assertEqual([1], self._finding(f"F-{self.issue}-01").rounds)

    def test_a1_handoff_must_declare_the_target_issue_and_it_must_match_the_pointer(self):
        self._activate()
        body = _report()
        same = f"<!-- handoff issue={self.issue} round=1 -->\n"
        for header, fragment in (
            ("", "ヘッダ"),                                                # ヘッダなし
            ("<!-- handoff round=1 -->\n", "ヘッダ"),                       # issue の欠落
            ("<!-- handoff issue=999 round=1 -->\n\n", "issue=999"),        # 別 Issue のレポート
            (same + same + "\n", "重複"),
            ("<!-- handoff issue=² round=1 -->\n\n", "issue"),             # 非 ASCII 数字
        ):
            with self.subTest(header=header):
                code, _, err = self._ingest_raw(header + body)
                self.assertEqual(cli.EXIT_ERROR, code)
                self.assertIn(fragment, err)
        self.assertFalse(paths.karte_path(self.issue, self.root).exists())

    def test_a1_a_new_block_alone_cannot_be_ingested_into_the_wrong_issue(self):
        self._activate()
        code, _, err = self._ingest_raw("<!-- handoff issue=1 round=1 -->\n\n" + _report("new"))
        self.assertEqual(cli.EXIT_ERROR, code)
        self.assertFalse(paths.karte_path(1, self.root).exists())

    def test_a3_stale_or_reused_handoff_is_not_ingested_as_a_new_round(self):
        self._activate()
        self.assertEqual(cli.EXIT_OK, self._ingest(_report())[0])           # round 1 を取り込み済み
        stale = f"<!-- handoff issue={self.issue} round=1 -->\n\n" + _report(f"F-{self.issue}-01")
        code, _, err = self._ingest_raw(stale, "pr-reviewer--r1.md")         # 同じ handoff の再利用
        self.assertEqual(cli.EXIT_ERROR, code)
        self.assertIn("round", err)
        self.assertEqual([1], self._finding(f"F-{self.issue}-01").rounds)

    def test_a2_reviewer_can_correct_scope_of_a_finding_ingested_before_any_owner_decision(self):
        self._main_context_ingest_round(1, _report(scope="in"))
        self.assertFalse(scope_ledger.exists(self.issue, self.root))
        self.assertEqual(cli.EXIT_OK, self._ingest(_report(f"F-{self.issue}-01", scope="out"))[0])
        self.assertEqual("out", self._finding(f"F-{self.issue}-01").scope)

    def test_a2_owner_scope_marker_keeps_the_decision_and_only_decide_writes_it(self):
        self._main_context_ingest_round(1, _report(scope="in"))
        self._decide(scope="out")
        self.assertEqual({f"F-{self.issue}-01": "out"}, scope_ledger.owner_scopes(self.issue, self.root))
        self.assertEqual({}, self._declared_scopes())  # 申告ではない
        self.assertEqual(cli.EXIT_OK, self._ingest(_report(f"F-{self.issue}-01", scope="in"))[0])
        self.assertEqual("out", self._finding(f"F-{self.issue}-01").scope)
        self.assertEqual("in", self._declared_scopes()[f"F-{self.issue}-01"])
        self.assertEqual(cli.EXIT_OK, self._ingest(_report(f"F-{self.issue}-01", scope="in"))[0])  # 次ラウンドも保持
        self.assertEqual("out", self._finding(f"F-{self.issue}-01").scope)
        code, out, err = self._ingest(_report(f"F-{self.issue}-01", scope="out"))
        self.assertEqual(cli.EXIT_OK, code, err)
        self.assertNotIn("オーナーが確定した scope を保持", out)

    def test_a5_bool_round_in_declared_scope_is_rejected_as_corrupt(self):
        self._activate()
        self._ingest(_report())
        self._declared_path().write_text('{"round": true, "id": "F-375-01", "scope": "in"}\n', encoding="utf-8")
        code, _, err = self._ingest(_report(f"F-{self.issue}-01"), "pr-reviewer--r2.md")
        self.assertEqual(cli.EXIT_ERROR, code)
        self.assertIn("壊れている", err)

    def test_a5_repair_keeps_every_backup_generation_instead_of_overwriting(self):
        self._activate()
        self._ingest(_report())
        path = self._declared_path()
        good = path.read_text(encoding="utf-8")
        originals = []
        for broken in ('{"round": 2, "id"', '{"round": 3, "x'):
            path.write_text(good + broken + "\n", encoding="utf-8")
            originals.append(path.read_text(encoding="utf-8"))
            code, _, _ = self._run(owner_cli.cmd_activate, issue=str(self.issue), repair_declared_scope=True)
            self.assertEqual(cli.EXIT_OK, code)
        backups = sorted(path.parent.glob(path.name + ".bak*"))
        self.assertEqual([path.name + ".bak", path.name + ".bak.1"], [b.name for b in backups])
        self.assertEqual(originals, [b.read_text(encoding="utf-8") for b in backups])

    def test_r6_docstrings_no_longer_point_at_removed_names(self):
        root = Path(__file__).resolve().parents[2]
        self.assertNotIn("6 verb", (root / "karte/__init__.py").read_text(encoding="utf-8"))

    def test_r7_reviewer_ingest_parses_the_ledger_only_once(self):
        self._activate()
        self._ingest(_report())
        with mock.patch.object(cli.model, "parse", wraps=cli.model.parse) as parse:
            self.assertEqual(cli.EXIT_OK, self._ingest(_report(f"F-{self.issue}-01"), "pr-reviewer--r2.md")[0])
        self.assertEqual(1, parse.call_count)

    def test_declared_records_are_parsed_once(self):
        self._activate()
        self._ingest(_report())
        with mock.patch.object(scope_records, "read_records", wraps=scope_records.read_records) as read:
            self.assertEqual(cli.EXIT_OK, self._ingest(_report(f"F-{self.issue}-01"))[0])
        self.assertEqual(1, read.call_count)

    def test_pointer_overflow_is_refused(self):
        self._pointer('{"issue": 375, "round": 999999999999999999}\n')
        code, _, err = self._ingest(_report())
        self.assertEqual(cli.EXIT_ERROR, code)
        self.assertIn("桁数の上限", err)

    def test_owner_verbs_are_registered_separately(self):
        parser = cli.build_parser((reviewer_cli.register, owner_cli.register))
        self.assertIs(parser.parse_args(["activate", "--issue", "1"]).func, owner_cli.cmd_activate)
        self.assertFalse(hasattr(reviewer_cli, "cmd_activate"))
        self.assertFalse(hasattr(reviewer_cli, "cmd_decide"))

    def _main_context_ingest_round(self, round_no, text):
        path = self.root / "tmp" / f"review-main-{round_no}.md"
        path.write_text(text, encoding="utf-8")
        return self._run(cli.cmd_ingest_review, issue=str(self.issue), round=str(round_no), source=str(path))

    def test_u5_reviewer_verbs_do_not_import_from_cli(self):
        for module in (reviewer_cli, owner_decision, verb_boundary):
            assert module.__file__ is not None
            tree = ast.parse(Path(module.__file__).read_text(encoding="utf-8"))
            imported = [n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)]
            self.assertNotIn("cli", imported, module.__name__)

    def test_u6_agent_docs_tell_the_reviewer_to_write_an_absolute_main_checkout_path(self):
        root = Path(__file__).resolve().parents[2]
        for rel in (".claude/agents/pr-reviewer.md", ".ai/agents/pr-reviewer.md"):
            self.assertIn("主チェックアウトの絶対パス", (root / rel).read_text(encoding="utf-8"), rel)


if __name__ == "__main__":
    unittest.main()
