"""karte ingest-reviewer / activate / decide（Issue #375）。実 tmp ディレクトリで検証する。"""

import argparse
import ast
import contextlib
import errno
import io
import json
import os
import tempfile
import shutil
import unittest
from pathlib import Path
from unittest import mock

from karte import cli, exit_codes, handoff_header, handoff_path, karte_rounds, owner_cli, owner_decision, paths, pointer_completion, review_envelope, review_expectation, reviewer_cli, reviewer_policy, scope_directory, scope_ledger, scope_ledger_io, scope_records, verb_boundary
from karte.errors import KarteUsageError
from karte.int_args import parse_int
from karte.model import KarteFormatError
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


ENVELOPE_ARGS = {
    "run_id": "run-375-a", "target_key": "pr-697", "phase": "implementation",
    "snapshot_oid": "a" * 40, "input_digest": "b" * 64,
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

    def _activate(self, **overrides):
        """主文脈が review envelope の期待値つきでポインタを向ける（通常の運用と同じ形）。"""
        return self._run(owner_cli.cmd_activate, issue=str(self.issue), **{**ENVELOPE_ARGS, **overrides})

    def _expectation(self):
        return review_envelope.expected_of(issue=self.issue, **ENVELOPE_ARGS)

    def _header(self, round_no):
        return handoff_header.render_header(round_no, self._expectation())

    def _write_pointer(self, round_no, *, expect=True):
        pointer = {"issue": self.issue, "round": round_no}
        if expect:
            pointer["review_expect"] = self._expectation()
        paths.active_path(self.root, create_dir=True).write_text(json.dumps(pointer), encoding="utf-8")

    def _rearm_expectation(self):
        """取り込み成功で消える期待値を、次の取り込みのために主文脈が再度記録した状態にする。"""
        try:
            path = paths.active_path(self.root)
            pointer = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError, KartePathError):
            return
        pointer["review_expect"] = self._expectation()
        path.write_text(json.dumps(pointer), encoding="utf-8")

    def _next_round(self):
        """進行ポインタの次ラウンド（ポインタが読めなければ 1）。"""
        try:
            return parse_int(json.loads(paths.active_path(self.root).read_text(encoding="utf-8"))["round"], "round", minimum=0) + 1
        except (OSError, ValueError, KeyError, TypeError, KartePathError, KarteUsageError):  # KarteMissing も KartePathError
            return 1

    def _ingest_raw(self, text, name="pr-reviewer--r1.md"):
        return self._run(reviewer_cli.cmd_ingest_reviewer, source=self._handoff(text, name))

    def _ingest(self, text, name="pr-reviewer--r1.md"):
        """取り込み先と一致するヘッダ（issue / round / 共通 envelope）を付けて取り込む。"""
        header = handoff_header.render_header(self._next_round(), self._expectation()) + "\n\n"
        self._rearm_expectation()
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
        self.assertIn("と同じ値に限る", reviewer_help)

    def test_reviewer_same_round_retry_requires_explicit_round(self):
        self._activate()
        self.assertEqual(cli.EXIT_OK, self._ingest(_report(scope="in"))[0])
        report = self._header(1) + "\n\n" + _report(f"F-{self.issue}-01", scope="out")
        self._write_pointer(0)
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
                self._write_pointer(pointer_round)
                report = self._header(requested) + "\n\n" + _report(f"F-{self.issue}-01", scope="out")
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

    def test_scope_ledger_symlinks_fail_closed_without_writes(self):
        self._activate()
        self.assertEqual(cli.EXIT_OK, self._ingest(_report())[0])
        self.assertEqual(cli.EXIT_OK, self._decide(disposition="deferred", deferred_to="#9")[0])
        ledger = self._declared_path()
        good = ledger.read_bytes()
        active = paths.active_path(self.root)
        karte = paths.karte_path(self.issue, self.root)
        before_active, before_karte = active.read_bytes(), karte.read_bytes()

        for existing in (False, True):
            with self.subTest(target_exists=existing):
                ledger.unlink()
                target = self.root / ("scope-target-live" if existing else "scope-target-missing")
                if existing:
                    target.write_bytes(good)
                ledger.symlink_to(target)
                code, _, err = self._main_context_ingest_round(2, _report(f"F-{self.issue}-01"))
                self.assertEqual(cli.EXIT_ERROR, code)
                self.assertIn("symlink", err)
                with self.assertRaises(KartePathError):
                    scope_records.read_records(self.issue, self.root)
                code, _, err = self._run(owner_cli.cmd_activate, issue=str(self.issue), repair_declared_scope=True)
                self.assertEqual(cli.EXIT_ERROR, code)
                self.assertIn("symlink", err)
                self.assertEqual(before_active, active.read_bytes())
                self.assertEqual(before_karte, karte.read_bytes())
                self.assertTrue(ledger.is_symlink())
                self.assertEqual(target, ledger.readlink())
                self.assertEqual(existing, target.exists())
                if existing:
                    self.assertEqual(good, target.read_bytes())
                ledger.unlink()
                ledger.write_bytes(good)

    def test_scope_ledger_directory_is_rejected_without_writes(self):
        self._activate()
        self.assertEqual(cli.EXIT_OK, self._ingest(_report())[0])
        ledger = self._declared_path()
        ledger.unlink()
        ledger.mkdir()
        active, karte = paths.active_path(self.root), paths.karte_path(self.issue, self.root)
        before = (active.read_bytes(), karte.read_bytes())
        with self.assertRaises(KartePathError):
            scope_ledger.exists(self.issue, self.root)
        with self.assertRaises(KartePathError):
            scope_records.read_records(self.issue, self.root)
        code, _, err = self._main_context_ingest_round(2, _report(f"F-{self.issue}-01"))
        self.assertEqual(cli.EXIT_ERROR, code)
        self.assertIn("通常ファイルではない", err)
        code, _, _ = self._run(owner_cli.cmd_activate, issue=str(self.issue), repair_declared_scope=True)
        self.assertEqual(cli.EXIT_ERROR, code)
        self.assertEqual(before, (active.read_bytes(), karte.read_bytes()))
        self.assertTrue(ledger.is_dir())

    def test_scope_ledger_metadata_error_is_not_treated_as_absence(self):
        self._activate()
        ledger = self._declared_path()
        original_stat = os.stat

        def stat_error(path, *args, **kwargs):
            if path == ledger.name and kwargs.get("dir_fd") is not None:
                raise PermissionError("denied")
            return original_stat(path, *args, **kwargs)

        with mock.patch.object(os, "stat", side_effect=stat_error):
            with self.assertRaisesRegex(KartePathError, "検査できない"):
                scope_records.is_regular_or_missing(ledger)

    def _assert_scope_replacement_is_rejected(self, operation, kind):
        if kind == "fifo" and not hasattr(os, "mkfifo"):
            self.skipTest("FIFO が使用できない")
        self._activate()
        self.assertEqual(cli.EXIT_OK, self._ingest(_report())[0])
        ledger = self._declared_path()
        target = self.root / "outside-scope.txt"
        target.write_text("not a scope record\n", encoding="utf-8")
        active, karte = paths.active_path(self.root), paths.karte_path(self.issue, self.root)
        before = (active.read_bytes(), karte.read_bytes(), target.read_bytes())
        real_open, real_path_read = os.open, Path.read_text
        swapped = []

        def swap():
            if not swapped:
                ledger.unlink()
                if kind == "symlink":
                    ledger.symlink_to(target)
                else:
                    os.mkfifo(ledger)
                swapped.append(True)

        def open_race(path, flags, *args, **kwargs):
            if isinstance(path, (str, os.PathLike)) and (
                Path(path) == ledger or (str(path) == ledger.name and kwargs.get("dir_fd") is not None)
            ):
                swap()
            return real_open(path, flags, *args, **kwargs)

        def read_race(path, *args, **kwargs):
            if path == ledger:
                swap()
                self.fail("差替え後に path の read_text で開こうとした")
            return real_path_read(path, *args, **kwargs)

        with mock.patch.object(os, "open", side_effect=open_race), \
             mock.patch.object(Path, "read_text", autospec=True, side_effect=read_race):
            if operation == "ingest":
                code, _, _ = self._main_context_ingest_round(2, _report(f"F-{self.issue}-01"))
            else:
                code, _, _ = self._run(owner_cli.cmd_activate, issue=str(self.issue), repair_declared_scope=True)
        self.assertTrue(swapped)
        self.assertEqual(cli.EXIT_ERROR, code)
        self.assertEqual(before, (active.read_bytes(), karte.read_bytes(), target.read_bytes()))
        self.assertFalse(ledger.with_name(ledger.name + ".bak").exists())
        if kind == "symlink":
            self.assertTrue(ledger.is_symlink())
            self.assertEqual(target, ledger.readlink())

    def test_scope_symlink_swap_is_rejected_during_ingest(self):
        self._assert_scope_replacement_is_rejected("ingest", "symlink")

    def test_scope_symlink_swap_is_rejected_before_repair_backup(self):
        self._assert_scope_replacement_is_rejected("repair", "symlink")

    def test_scope_repair_keeps_backup_if_symlink_appears_after_backup(self):
        self._activate()
        self.assertEqual(cli.EXIT_OK, self._ingest(_report())[0])
        ledger = self._declared_path()
        original = ledger.read_text(encoding="utf-8") + "{broken\n"
        ledger.write_text(original, encoding="utf-8")
        backup = ledger.with_name(ledger.name + ".bak")
        target = self.root / "outside-scope.txt"
        target.write_text("external data\n", encoding="utf-8")
        active, karte = paths.active_path(self.root), paths.karte_path(self.issue, self.root)
        before = (active.read_bytes(), karte.read_bytes(), target.read_bytes())
        real_link = os.link

        def swap_after_backup(src, dst, *args, **kwargs):
            real_link(src, dst, *args, **kwargs)
            if dst == backup.name:
                ledger.unlink()
                ledger.symlink_to(target)

        with mock.patch.object(os, "link", side_effect=swap_after_backup):
            code, _, err = self._run(owner_cli.cmd_activate, issue=str(self.issue), repair_declared_scope=True)
        self.assertEqual(cli.EXIT_ERROR, code)
        self.assertIn("symlink", err)
        self.assertEqual(original, backup.read_text(encoding="utf-8"))
        self.assertEqual(before, (active.read_bytes(), karte.read_bytes(), target.read_bytes()))
        self.assertTrue(ledger.is_symlink())
        self.assertEqual(target, ledger.readlink())

    def test_scope_repair_does_not_overwrite_symlink_backup(self):
        self._activate()
        self.assertEqual(cli.EXIT_OK, self._ingest(_report())[0])
        ledger = self._declared_path()
        good = ledger.read_text(encoding="utf-8")
        original = good + "{broken\n"
        ledger.write_text(original, encoding="utf-8")
        backup = ledger.with_name(ledger.name + ".bak")
        target = self.root / "existing-backup-target"
        target.write_text("do not overwrite\n", encoding="utf-8")
        backup.symlink_to(target)
        code, _, _ = self._run(owner_cli.cmd_activate, issue=str(self.issue), repair_declared_scope=True)
        self.assertEqual(cli.EXIT_OK, code)
        self.assertTrue(backup.is_symlink())
        self.assertEqual("do not overwrite\n", target.read_text(encoding="utf-8"))
        self.assertEqual(original, ledger.with_name(ledger.name + ".bak.1").read_text(encoding="utf-8"))
        self.assertEqual(good, ledger.read_text(encoding="utf-8"))

    def _assert_scope_parent_swap_is_rejected(self, operation):
        self._activate()
        self.assertEqual(cli.EXIT_OK, self._ingest(_report())[0])
        self._rearm_expectation()  # 取り込み成功で消えた期待値を戻し、以降のポインタ内容を固定する
        ledger = self._declared_path()
        if operation in ("repair", "repair_backup"):
            ledger.write_text(ledger.read_text(encoding="utf-8") + "{broken\n", encoding="utf-8")
        directory = ledger.parent
        moved = directory.with_name("_karte-original")
        outside = Path(tempfile.mkdtemp(prefix="scope-outside-"))
        self.addCleanup(lambda: shutil.rmtree(outside, ignore_errors=True))
        outside_ledger = outside / ledger.name
        outside_ledger.write_text("outside contents\n", encoding="utf-8")
        active, karte = paths.active_path(self.root), paths.karte_path(self.issue, self.root)
        before = (active.read_bytes(), karte.read_bytes(), ledger.read_bytes(), outside_ledger.read_bytes())
        real_open, real_link = os.open, os.link
        swapped = []

        def swap_parent():
            directory.rename(moved)
            directory.symlink_to(outside, target_is_directory=True)
            swapped.append(True)

        def open_race(path, flags, *args, **kwargs):
            name = os.fspath(path)
            if kwargs.get("dir_fd") is not None and not swapped:
                reading = name == ledger.name and not (flags & os.O_WRONLY)
                writing = name.startswith("." + ledger.name + ".") and bool(flags & os.O_CREAT)
                if reading and operation == "repair" or writing and operation in ("reviewer", "owner"):
                    swap_parent()
            return real_open(path, flags, *args, **kwargs)

        def link_race(src, dst, *args, **kwargs):
            result = real_link(src, dst, *args, **kwargs)
            if operation == "repair_backup" and dst == ledger.name + ".bak" and not swapped:
                swap_parent()
            return result

        with mock.patch.object(os, "open", side_effect=open_race), \
             mock.patch.object(os, "link", side_effect=link_race):
            if operation in ("repair", "repair_backup"):
                code, _, _ = self._run(owner_cli.cmd_activate, issue=str(self.issue), repair_declared_scope=True)
            elif operation == "reviewer":
                code, _, _ = self._ingest(_report(f"F-{self.issue}-01", scope="out"), "pr-reviewer--r2.md")
            else:
                code, _, _ = self._decide(scope="out")
        self.assertTrue(swapped)
        self.assertEqual(cli.EXIT_ERROR, code)
        self.assertEqual(before, ((moved / active.name).read_bytes(), (moved / karte.name).read_bytes(),
                                  (moved / ledger.name).read_bytes(), outside_ledger.read_bytes()))
        self.assertEqual([ledger.name], sorted(path.name for path in outside.iterdir()))
        self.assertTrue(directory.is_symlink())
        self.assertEqual(outside, directory.readlink())
        if operation == "repair_backup":
            self.assertEqual(before[2], (moved / (ledger.name + ".bak")).read_bytes())

    def test_scope_parent_swap_during_repair_is_rejected(self):
        self._assert_scope_parent_swap_is_rejected("repair")

    def test_scope_parent_swap_after_repair_backup_is_rejected(self):
        self._assert_scope_parent_swap_is_rejected("repair_backup")

    def test_scope_repair_parent_swap_at_replace_keeps_backup_and_rejects(self):
        self._activate()
        self.assertEqual(cli.EXIT_OK, self._ingest(_report())[0])
        ledger = self._declared_path()
        good = ledger.read_text(encoding="utf-8")
        original = good + "{broken\n"
        ledger.write_text(original, encoding="utf-8")
        directory = ledger.parent
        moved = directory.with_name("_karte-original")
        outside = Path(tempfile.mkdtemp(prefix="scope-outside-"))
        self.addCleanup(lambda: shutil.rmtree(outside, ignore_errors=True))
        outside_ledger = outside / ledger.name
        outside_ledger.write_text("outside contents\n", encoding="utf-8")
        active, karte = paths.active_path(self.root), paths.karte_path(self.issue, self.root)
        before = (active.read_bytes(), karte.read_bytes(), outside_ledger.read_bytes())
        real_replace, swapped = os.replace, []

        def swap_before_replace(src, dst, *args, **kwargs):
            if dst == ledger.name and kwargs.get("dst_dir_fd") is not None and not swapped:
                directory.rename(moved)
                directory.symlink_to(outside, target_is_directory=True)
                swapped.append(True)
            return real_replace(src, dst, *args, **kwargs)

        with mock.patch.object(os, "replace", side_effect=swap_before_replace):
            code, _, err = self._run(owner_cli.cmd_activate, issue=str(self.issue), repair_declared_scope=True)
        self.assertTrue(swapped)
        self.assertEqual(cli.EXIT_ERROR, code)
        self.assertIn("置き場が操作中に変更された", err)
        self.assertEqual(good, (moved / ledger.name).read_text(encoding="utf-8"))
        self.assertEqual(original, (moved / (ledger.name + ".bak")).read_text(encoding="utf-8"))
        self.assertEqual(before, ((moved / active.name).read_bytes(), (moved / karte.name).read_bytes(),
                                  outside_ledger.read_bytes()))
        self.assertEqual([ledger.name], sorted(path.name for path in outside.iterdir()))

    def test_scope_parent_swap_during_reviewer_append_is_rejected(self):
        self._assert_scope_parent_swap_is_rejected("reviewer")

    def test_scope_parent_swap_during_owner_append_is_rejected(self):
        self._assert_scope_parent_swap_is_rejected("owner")

    def test_scope_fifo_swap_is_rejected_during_ingest(self):
        self._assert_scope_replacement_is_rejected("ingest", "fifo")

    def test_scope_fifo_swap_is_rejected_before_repair_backup(self):
        self._assert_scope_replacement_is_rejected("repair", "fifo")

    def test_scope_read_refuses_missing_os_guard(self):
        ledger = self.root / "ledger"
        for flag in ("O_NOFOLLOW", "O_NONBLOCK"):
            with self.subTest(flag=flag), mock.patch.object(os, flag, 0, create=True):
                with self.assertRaisesRegex(KartePathError, "OS 機能"):
                    scope_ledger_io.read_scope_text(ledger)
        with mock.patch.object(scope_directory, "_DIR_FD_SUPPORTED", False):
            with self.assertRaisesRegex(KartePathError, "OS 機能"):
                scope_ledger_io.read_scope_text(ledger)

    def test_scope_invalid_utf8_refuses_without_writes(self):
        self._activate()
        self.assertEqual(cli.EXIT_OK, self._ingest(_report())[0])
        ledger = self._declared_path()
        ledger.write_bytes(b"\xff\n")
        active, karte = paths.active_path(self.root), paths.karte_path(self.issue, self.root)
        before = (active.read_bytes(), karte.read_bytes(), ledger.read_bytes())
        code, _, err = self._main_context_ingest_round(2, _report(f"F-{self.issue}-01"))
        self.assertEqual(cli.EXIT_ERROR, code)
        self.assertIn("UTF-8", err)
        self.assertEqual(before, (active.read_bytes(), karte.read_bytes(), ledger.read_bytes()))
        code, _, err = self._run(owner_cli.cmd_activate, issue=str(self.issue), repair_declared_scope=True)
        self.assertEqual(cli.EXIT_ERROR, code)
        self.assertIn("UTF-8", err)
        self.assertEqual(before, (active.read_bytes(), karte.read_bytes(), ledger.read_bytes()))
        self.assertFalse(ledger.with_name(ledger.name + ".bak").exists())

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
        # F-01（レビューア申告・未解消・disposition 未決定）の再掲漏れなので、台帳は書くが未完了で返る（F-375-05）
        self.assertEqual(exit_codes.EXIT_INCOMPLETE, code, err)
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
            pointer_completion.ingest_target(argparse.Namespace(issue=self.issue, round=None), self.root)

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
                original_replace = os.replace

                def write(path, content):
                    if failing == "ledger" and path == paths.karte_path(self.issue, self.root):
                        raise OSError("disk full")
                    return original(path, content)

                def replace(src, dst, *args, **kwargs):
                    if failing == "sidefile" and dst == self._declared_path().name:
                        raise OSError("disk full")
                    return original_replace(src, dst, *args, **kwargs)

                with mock.patch.object(paths, "write_text_atomic", side_effect=write), \
                     mock.patch.object(os, "replace", side_effect=replace):
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
            pointer_completion.ingest_target(argparse.Namespace(issue=self.issue, round=None), self.root)

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

    def test_recursion_error_from_json_loads_is_reported_as_corrupt_declared_scope(self):
        """解釈系が RecursionError を出す版でも KarteFormatError として拒否する（版依存を patch で固定する）。"""
        self._activate()
        self.assertEqual(cli.EXIT_OK, self._ingest(_report())[0])
        path = self._declared_path()
        original = path.read_text(encoding="utf-8") + '{"recursion-probe": 1}\n'
        path.write_text(original, encoding="utf-8")
        real_loads = json.loads

        def fake_loads(text, *args, **kwargs):
            if isinstance(text, str) and "recursion-probe" in text:
                raise RecursionError("maximum recursion depth exceeded")
            return real_loads(text, *args, **kwargs)

        with mock.patch.object(json, "loads", side_effect=fake_loads):
            with self.assertRaisesRegex(KarteFormatError, "repair-declared-scope"):
                scope_records.read_records(self.issue, self.root)
            code, _, err = self._ingest(_report(f"F-{self.issue}-01"), "pr-reviewer--r2.md")
        self.assertEqual(cli.EXIT_ERROR, code)
        self.assertIn("--repair-declared-scope", err)
        self.assertEqual(original, path.read_text(encoding="utf-8"))

    def test_deep_declared_scope_fails_closed_and_can_be_repaired(self):
        """深い入力が RecursionError になるか通常の型エラーになるかは Python の版で違う。どちらでも拒否・復旧できる。"""
        self._activate()
        self.assertEqual(cli.EXIT_OK, self._ingest(_report())[0])
        path = self._declared_path()
        good = path.read_text(encoding="utf-8")
        depth = 20_000
        broken = "[" * depth + "0" + "]" * depth + "\n"
        original = good + broken
        path.write_text(original, encoding="utf-8")

        with self.assertRaisesRegex(KarteFormatError, "repair-declared-scope"):
            scope_records.read_records(self.issue, self.root)
        code, _, err = self._ingest(_report(f"F-{self.issue}-01"), "pr-reviewer--r2.md")
        self.assertEqual(cli.EXIT_ERROR, code)
        self.assertIn("--repair-declared-scope", err)
        self.assertEqual(original, path.read_text(encoding="utf-8"))

        code, out, _ = self._run(owner_cli.cmd_activate, issue=str(self.issue), repair_declared_scope=True)
        self.assertEqual(cli.EXIT_OK, code)
        self.assertIn("1 件", out)
        self.assertEqual(original, path.with_name(path.name + ".bak").read_text(encoding="utf-8"))
        self.assertEqual(good, path.read_text(encoding="utf-8"))
        self.assertEqual(cli.EXIT_OK, self._ingest(_report(f"F-{self.issue}-01"), "pr-reviewer--r2.md")[0])

    def test_r5_pointer_round_zero_is_derived_by_ingest_review_too(self):
        """期待値なしの activate 後の round 0 から、ingest-review も round 省略で round 1 を導出する。"""
        self._run(owner_cli.cmd_activate, issue=str(self.issue))  # 期待値なし＝レビューア待ちではない
        path = self.root / "tmp" / "review-main.md"
        path.write_text(_report(), encoding="utf-8")
        code, _, _ = self._run(cli.cmd_ingest_review, issue=str(self.issue), round=None, source=str(path))
        self.assertEqual(cli.EXIT_OK, code)
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
        stale = self._header(1) + "\n\n" + _report(f"F-{self.issue}-01")
        self._write_pointer(1)
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


class TestReviewEnvelope(ReviewerIngestCase):
    """handoff の共通 envelope（#371）束縛・round 1 保護・再掲漏れの可視化（Issue #375 是正ラウンド 1）。"""

    def _legacy_ingest(self, round_no, text):
        path = self.root / "tmp" / f"review-main-{round_no}.md"
        path.write_text(text, encoding="utf-8")
        return self._run(cli.cmd_ingest_review, issue=str(self.issue), round=str(round_no), source=str(path))

    def test_stale_or_foreign_envelope_is_rejected_without_writing(self):
        self._activate()
        for key, value in (
            ("run_id", "run-old"), ("target_key", "pr-other"), ("snapshot_oid", "c" * 40),
            ("input_digest", "d" * 64), ("phase", "test_design"),
        ):
            with self.subTest(key=key):
                header = handoff_header.render_header(1, {**self._expectation(), key: value})
                code, _, err = self._ingest_raw(header + "\n\n" + _report())
                self.assertEqual(cli.EXIT_ERROR, code)
                self.assertIn(f"stale: {key}", err)
                self.assertFalse(paths.karte_path(self.issue, self.root).exists())
                self.assertEqual({}, self._declared_scopes())

    def test_two_field_legacy_header_and_unknown_or_duplicate_keys_are_rejected(self):
        self._activate()
        good = self._header(1)
        for header, fragment in (
            (f"<!-- handoff issue={self.issue} round=1 -->", "envelope"),
            (good.replace(" -->", " extra=1 -->"), "未知"),
            (good.replace(" -->", " run_id=run-375-a -->"), "重複"),
            (good.replace("status=ready", "status=stop"), "ready"),
            (good.replace("snapshot_oid=" + "a" * 40, "snapshot_oid=abc"), "OID"),
        ):
            with self.subTest(header=header):
                code, _, err = self._ingest_raw(header + "\n\n" + _report())
                self.assertEqual(cli.EXIT_ERROR, code)
                self.assertIn(fragment, err)
        self.assertFalse(paths.karte_path(self.issue, self.root).exists())

    def test_ingest_without_recorded_expectation_is_rejected_and_expectation_is_single_use(self):
        self._run(owner_cli.cmd_activate, issue=str(self.issue))
        code, _, err = self._ingest_raw(self._header(1) + "\n\n" + _report())
        self.assertEqual(cli.EXIT_ERROR, code)
        self.assertIn("期待値が無い", err)
        self._activate()
        source = self._handoff(self._header(1) + "\n\n" + _report(), "pr-reviewer--once.md")
        self.assertEqual(cli.EXIT_OK, self._run(reviewer_cli.cmd_ingest_reviewer, source=source)[0])
        code, _, err = self._run(reviewer_cli.cmd_ingest_reviewer, source=source)  # 同じ handoff の再利用
        self.assertEqual(cli.EXIT_ERROR, code)
        self.assertIn("期待値が無い", err)

    def test_header_printed_by_activate_is_accepted_verbatim(self):
        code, out, err = self._activate()
        self.assertEqual(cli.EXIT_OK, code, err)
        header = next(line.strip() for line in out.splitlines() if line.strip().startswith("<!-- handoff"))
        self.assertEqual(self._header(1), header)
        self.assertEqual(cli.EXIT_OK, self._ingest_raw(header + "\n\n" + _report())[0])

    def test_activate_requires_every_envelope_argument_and_valid_values(self):
        for overrides, fragment in (
            ({"run_id": None}, "不足"), ({"snapshot_oid": "short"}, "OID"),
            ({"input_digest": "zz"}, "sha256"), ({"phase": "review"}, "phase"),
            ({"run_id": "run 1"}, "run_id"), ({"target_key": "pr-->1"}, "target_key"),  # ヘッダへ往復できない値（F-375-12）
        ):
            with self.subTest(overrides=overrides):
                code, _, err = self._activate(**overrides)
                self.assertEqual(cli.EXIT_ERROR, code)
                self.assertIn(fragment, err)
                self.assertFalse(paths.active_path(self.root).exists())

    def test_legacy_ingest_review_is_refused_while_the_reviewer_ingest_is_pending(self):
        self._activate()
        code, _, err = self._legacy_ingest(1, _report(scope="out"))
        self.assertEqual(cli.EXIT_ERROR, code)
        self.assertIn("レビューア本人の取り込み待ち", err)
        self.assertFalse(paths.karte_path(self.issue, self.root).exists())
        self._run(owner_cli.cmd_activate, issue=str(self.issue))  # 期待値なしの activate で待ちを解除できる
        self.assertEqual(cli.EXIT_OK, self._legacy_ingest(1, _report(scope="out"))[0])

    def test_activate_without_envelope_does_not_enter_protected_mode(self):
        """期待値なしの activate は待機取消の退避経路。原本を作らず、主文脈の ingest-review は従来どおり（F-375-10）。"""
        code, out, err = self._run(owner_cli.cmd_activate, issue=str(self.issue))
        self.assertEqual(cli.EXIT_OK, code, err)
        self.assertNotIn("review envelope の期待値を記録", out)
        self.assertFalse(scope_ledger.exists(self.issue, self.root))
        self.assertEqual(cli.EXIT_OK, self._legacy_ingest(1, _report())[0])
        code, _, err = self._legacy_ingest(2, _report(f"F-{self.issue}-01"))  # 既存 ID の再掲は拒否されない
        self.assertEqual(cli.EXIT_OK, code, err)
        self.assertNotIn("追記専用", err)
        self.assertFalse(scope_ledger.exists(self.issue, self.root))

    def _declared_bytes(self):
        return (paths.karte_dir(self.root) / f"issue-{self.issue}.declared-scope.jsonl").read_bytes()

    def test_activate_never_creates_the_original_so_cancelling_the_wait_restores_legacy_ingest(self):
        """期待値つきの activate も原本を作らない。待機取消の後、主文脈の ingest-review は従来動作に戻る（F-375-10）。"""
        self.assertEqual(cli.EXIT_OK, self._activate()[0])
        self.assertFalse(scope_ledger.exists(self.issue, self.root))
        self.assertEqual(cli.EXIT_OK, self._run(owner_cli.cmd_activate, issue=str(self.issue))[0])
        self.assertFalse(scope_ledger.exists(self.issue, self.root))
        self.assertEqual(cli.EXIT_OK, self._legacy_ingest(1, _report())[0])
        code, _, err = self._legacy_ingest(2, _report(f"F-{self.issue}-01", status="resolved"))
        self.assertEqual(cli.EXIT_OK, code, err)  # 既存 finding の status を更新できる
        self.assertNotIn("追記専用", err)
        self.assertEqual("resolved", self._finding(f"F-{self.issue}-01").status)
        self.assertFalse(scope_ledger.exists(self.issue, self.root))

    def test_rejected_reviewer_ingest_leaves_no_original_and_keeps_the_wait_cancellable(self):
        self._activate()
        code, _, _ = self._ingest_raw(self._header(1) + "\n\n### new\nharm: real\n")  # 必須キー欠落＝拒否
        self.assertEqual(cli.EXIT_ERROR, code)
        self.assertFalse(scope_ledger.exists(self.issue, self.root))
        self.assertEqual(cli.EXIT_OK, self._run(owner_cli.cmd_activate, issue=str(self.issue))[0])
        self.assertEqual(cli.EXIT_OK, self._legacy_ingest(1, _report())[0])

    def test_original_made_by_a_reviewer_ingest_survives_cancelling_a_later_wait(self):
        """レビューアが取り込み済みの原本（オーナー確定値の保護）は、後の待機取消でも保護モードのまま残る。"""
        self._activate()
        self.assertEqual(cli.EXIT_OK, self._ingest(_report(scope="out"))[0])
        self.assertEqual(cli.EXIT_OK, self._decide(scope="in")[0])
        original = self._declared_bytes()
        self.assertEqual(cli.EXIT_OK, self._activate()[0])
        self.assertEqual(cli.EXIT_OK, self._run(owner_cli.cmd_activate, issue=str(self.issue))[0])
        self.assertEqual(original, self._declared_bytes())
        code, _, err = self._legacy_ingest(1, _report(f"F-{self.issue}-01", scope="out"))
        self.assertEqual(cli.EXIT_ERROR, code)
        self.assertIn("追記専用", err)
        self.assertEqual("in", self._finding(f"F-{self.issue}-01").scope)
        self.assertEqual(original, self._declared_bytes())

    def test_reviewer_ingest_arms_the_original_even_when_nothing_is_declared(self):
        """原本が無ければ、検証を通ったレビューア取り込みが自前で作る（F-375-16）。"""
        policy = reviewer_policy.ReviewerIngestPolicy(self.root, self.issue, 1)
        self.assertFalse(scope_ledger.exists(self.issue, self.root))
        policy.persist(1)
        self.assertTrue(scope_ledger.exists(self.issue, self.root))
        self.assertEqual({}, self._declared_scopes())
        policy.persist(1)  # 既にあれば何もしない
        self.assertEqual({}, self._declared_scopes())

    def test_zero_finding_report_through_the_real_ingest_path(self):
        """ヘッダと空本文（申告 0 件）の実 ingest-reviewer 経路の挙動を固定する（F-375-23）。"""
        self._activate()
        code, _, err = self._ingest("")
        self.assertEqual(cli.EXIT_ERROR, code)  # finding ブロックの無いレポートは申告 0 件の完了ではなく拒否される
        self.assertIn("finding ブロック", err)
        self.assertFalse(scope_ledger.exists(self.issue, self.root))  # 原本も台帳も作らない
        self.assertFalse(paths.karte_path(self.issue, self.root).exists())
        self.assertIsNotNone(review_expectation.pending(self.root, self.issue))  # 期待値は消費されない
        self.assertEqual(cli.EXIT_OK, self._run(owner_cli.cmd_activate, issue=str(self.issue))[0])
        self.assertEqual(cli.EXIT_OK, self._legacy_ingest(1, _report())[0])  # 待機取消後は従来動作のまま

    def test_ledger_write_failure_after_the_original_leaves_a_protected_original_and_a_retryable_round(self):
        """原本→台帳の順序の代償（F-375-22）：台帳の書込み失敗で原本だけが残り、同じ handoff の再実行で回復する。"""
        self._activate()
        ledger_path = paths.karte_path(self.issue, self.root)
        real_write = paths.write_text_atomic

        def fail_for_ledger(path, text):
            if Path(path) == ledger_path:
                raise OSError(errno.ENOSPC, "No space left on device")
            return real_write(path, text)

        with mock.patch.object(paths, "write_text_atomic", side_effect=fail_for_ledger):
            code, _, err = self._ingest(_report())
        self.assertEqual(cli.EXIT_ERROR, code)
        self.assertIn("No space left", err)
        self.assertFalse(ledger_path.exists())  # 台帳に round は無い
        self.assertTrue(scope_ledger.exists(self.issue, self.root))  # 原本だけが残る
        self.assertEqual({f"F-{self.issue}-01": "in"}, self._declared_scopes())
        self.assertIsNotNone(review_expectation.pending(self.root, self.issue))  # ポインタも期待値も動かない
        self.assertEqual(1, len(scope_records.read_records(self.issue, self.root)))
        self.assertEqual(cli.EXIT_OK, self._ingest(_report())[0])  # 同じ round の再実行で回復する
        self.assertEqual(1, karte_rounds.last_round(self._karte()))
        self.assertEqual(1, len(scope_records.read_records(self.issue, self.root)))  # 原本の記録は重複しない

    def test_cancelling_the_wait_after_a_ledger_write_failure_keeps_the_protected_mode(self):
        """再試行しない場合、原本は消えないので待機取消でも主文脈の ingest-review は保護モードのまま（F-375-22）。"""
        self._activate()
        ledger_path = paths.karte_path(self.issue, self.root)
        real_write = paths.write_text_atomic

        def fail_for_ledger(path, text):
            if Path(path) == ledger_path:
                raise OSError(errno.EROFS, "Read-only file system")
            return real_write(path, text)

        with mock.patch.object(paths, "write_text_atomic", side_effect=fail_for_ledger):
            self.assertEqual(cli.EXIT_ERROR, self._ingest(_report())[0])
        self.assertEqual(cli.EXIT_OK, self._run(owner_cli.cmd_activate, issue=str(self.issue))[0])
        self.assertTrue(scope_ledger.exists(self.issue, self.root))
        self.assertEqual(cli.EXIT_OK, self._legacy_ingest(1, _report("new", summary="別件", locus="b.py::other"))[0])
        code, _, err = self._legacy_ingest(2, _report(f"F-{self.issue}-01"))
        self.assertEqual(cli.EXIT_ERROR, code)  # 既存 ID の再掲は従来動作に戻らず拒否される
        self.assertIn("追記専用", err)

    def test_ingest_reviewer_without_activate_is_refused_and_does_not_leave_an_unprotected_round_one(self):
        """引数なし activate の直後の ingest-reviewer は期待値が無く拒否される。原本も作らない（F-375-16）。"""
        self._run(owner_cli.cmd_activate, issue=str(self.issue))
        code, _, err = self._ingest_raw(self._header(1) + "\n\n" + _report())
        self.assertEqual(cli.EXIT_ERROR, code)
        self.assertIn("期待値が無い", err)
        self.assertFalse(scope_ledger.exists(self.issue, self.root))
        self.assertFalse(paths.karte_path(self.issue, self.root).exists())

    def test_round_one_legacy_ingest_is_refused_while_waiting_and_protected_after_the_reviewer_ingest(self):
        self._activate()
        code, _, err = self._legacy_ingest(1, _report())
        self.assertEqual(cli.EXIT_ERROR, code)  # 待ちの間は round 1 でも迂回できない
        self.assertIn("レビューア本人の取り込み待ち", err)
        self.assertEqual(cli.EXIT_OK, self._ingest(_report())[0])
        report = _report(scope="out", summary="別件", locus="b.py::other",
                         disposition="waived", waived_by="main", waived_reason="x")
        code, _, err = self._legacy_ingest(1, report)
        self.assertEqual(cli.EXIT_OK, code, err)
        self.assertEqual("", self._finding(f"F-{self.issue}-02").disposition)
        self.assertIn("オーナー専権の disposition を無視", err)
        code, _, err = self._legacy_ingest(2, _report(f"F-{self.issue}-01"))
        self.assertEqual(cli.EXIT_ERROR, code)
        self.assertIn("追記専用", err)

    def test_reviewer_declaration_replacing_a_scope_without_origin_is_detected(self):
        self._run(owner_cli.cmd_activate, issue=str(self.issue))
        self.assertEqual(cli.EXIT_OK, self._legacy_ingest(1, _report(scope="out"))[0])
        self.assertEqual({}, self._declared_scopes())
        self._activate()
        code, out, err = self._ingest(_report(f"F-{self.issue}-01", scope="in"), "pr-reviewer--r2.md")
        self.assertEqual(cli.EXIT_OK, code, err)
        self.assertIn(f"申告原本のない scope をレビューア申告で置換", out)
        self.assertIn(f"F-{self.issue}-01（out→in）", out)
        self.assertEqual({f"F-{self.issue}-01": "in"}, self._declared_scopes())
        self._activate()
        code, out, _ = self._ingest(_report(f"F-{self.issue}-01", scope="in"), "pr-reviewer--r3.md")
        self.assertNotIn("申告原本のない scope", out)

    def test_open_finding_missing_from_the_reviewer_report_is_carried_over_but_not_completed(self):
        """再掲漏れは引き継ぐ（台帳は書く）が終了コード 0 にしない。再掲すれば 0 に戻る。"""
        self._activate()
        other = _report("new", summary="別の問題: 例外を握りつぶしている", locus="c/d.py::swallow")
        self.assertEqual(cli.EXIT_OK, self._ingest(_report() + "\n" + other)[0])
        code, out, err = self._ingest(_report(f"F-{self.issue}-01"), "pr-reviewer--r2.md")
        self.assertEqual(exit_codes.EXIT_INCOMPLETE, code, err)
        self.assertIn("再掲されなかった未解消 finding を引き継ぎ", err)
        self.assertIn(f"未完了: 再掲漏れ F-{self.issue}-02", err)
        self.assertTrue(out.splitlines()[-1].startswith("  未完了（取り込み済み）"))
        self.assertEqual("open", self._finding(f"F-{self.issue}-02").status)  # 解消扱いにしない
        self.assertEqual(2, karte_rounds.last_round(self._karte()))          # 台帳は書き込み済み
        restated = _report(f"F-{self.issue}-01") + "\n" + _report(f"F-{self.issue}-02")
        self.assertEqual(cli.EXIT_OK, self._ingest(restated, "pr-reviewer--r3.md")[0])

    def test_omitted_findings_that_need_no_restatement_do_not_make_the_run_incomplete(self):
        """オーナーが申し送りと決めたレビューア申告 finding・主文脈が足した finding の不在は警告のみ。"""
        self._activate()
        other = _report("new", summary="別の問題: 例外を握りつぶしている", locus="c/d.py::swallow")
        self.assertEqual(cli.EXIT_OK, self._ingest(_report() + "\n" + other)[0])
        self.assertEqual(cli.EXIT_OK, self._decide(
            finding=f"F-{self.issue}-02", disposition="deferred", deferred_to="#9")[0])
        code, _, err = self._ingest(_report(f"F-{self.issue}-01"), "pr-reviewer--r2.md")
        self.assertEqual(cli.EXIT_OK, code, err)
        self.assertIn(f"再掲されなかった未解消 finding を引き継ぎ: F-{self.issue}-02", err)

    def test_main_context_append_only_ingest_is_not_reported_as_incomplete(self):
        """主文脈専用の追記専用モードは再掲しないのが通常なので、未完了にしない。"""
        self._activate()
        self.assertEqual(cli.EXIT_OK, self._ingest(_report())[0])  # レビューア取り込みが原本を作り、以後は保護モード
        other = _report("new", summary="別の問題: 例外を握りつぶしている", locus="c/d.py::swallow")
        code, _, err = self._legacy_ingest(1, other)
        self.assertEqual(cli.EXIT_OK, code, err)
        self.assertIn("再掲されなかった未解消 finding を引き継ぎ", err)


class TestScopeDirectoryErrorReporting(ReviewerIngestCase):
    """open の失敗と書込みの失敗を区別して報告する（F-375-07）。"""

    def _ingested(self):
        self._activate()
        self.assertEqual(cli.EXIT_OK, self._ingest(_report())[0])

    def test_open_failure_is_reported_as_unable_to_open(self):
        path = self.root / "tmp" / "_karte" / "issue-375.declared-scope.jsonl"
        with mock.patch("karte.scope_directory.os.open", side_effect=PermissionError(13, "Permission denied")):
            with self.assertRaisesRegex(KartePathError, "開けない"):
                with scope_directory.open_scope_directory(path):
                    self.fail("開けなかったのに本体へ入った")

    def test_oserror_in_the_with_body_propagates_unchanged(self):
        (self.root / "tmp" / "_karte").mkdir(parents=True)
        path = self.root / "tmp" / "_karte" / "issue-375.declared-scope.jsonl"
        full = OSError(errno.ENOSPC, "No space left on device")
        with self.assertRaises(OSError) as caught:
            with scope_directory.open_scope_directory(path):
                raise full
        self.assertIs(full, caught.exception)
        self.assertNotIsInstance(caught.exception, KartePathError)

    def test_check_oserror_is_not_reported_as_unable_to_open(self):
        """開いた後の検査（check）が出す OSError は『開けない』に読み替えず、そのまま伝播する（F-375-20）。"""
        (self.root / "tmp" / "_karte").mkdir(parents=True)
        path = self.root / "tmp" / "_karte" / "issue-375.declared-scope.jsonl"
        failure = OSError(errno.EIO, "Input/output error")
        with mock.patch.object(scope_directory.ScopeDirectory, "check", side_effect=failure):
            with self.assertRaises(OSError) as caught:
                with scope_directory.open_scope_directory(path):
                    self.fail("検査に失敗したのに本体へ入った")
        self.assertIs(failure, caught.exception)
        self.assertNotIsInstance(caught.exception, KartePathError)

    def test_check_stat_failure_is_reported_as_unable_to_inspect_not_unable_to_open(self):
        (self.root / "tmp" / "_karte").mkdir(parents=True)
        path = self.root / "tmp" / "_karte" / "issue-375.declared-scope.jsonl"
        with mock.patch("karte.scope_directory.os.stat", side_effect=PermissionError(13, "Permission denied")):
            with self.assertRaises(KartePathError) as caught:
                with scope_directory.open_scope_directory(path):
                    self.fail("検査に失敗したのに本体へ入った")
        self.assertIn("検査できない", str(caught.exception))
        self.assertNotIn("開けない", str(caught.exception))

    def test_write_failure_is_not_reported_as_unable_to_open(self):
        self._ingested()
        with mock.patch("karte.scope_atomic.os.replace", side_effect=OSError(errno.ENOSPC, "No space left on device")):
            with self.assertRaises(OSError) as caught:
                scope_ledger.record_owner(self.issue, self.root, 1, f"F-{self.issue}-01", "out")
        self.assertNotIsInstance(caught.exception, KartePathError)
        self.assertNotIn("開けない", str(caught.exception))
        self.assertIn("No space left", str(caught.exception))
        self.assertEqual({}, scope_ledger.owner_scopes(self.issue, self.root))  # 書込みに失敗したので印は残らない

    def test_decide_reports_the_write_failure_cause_through_the_verb_boundary(self):
        self._ingested()
        with mock.patch("karte.scope_atomic.os.replace", side_effect=OSError(errno.ENOSPC, "No space left on device")):
            code, _, err = self._decide(scope="out")
        self.assertEqual(cli.EXIT_ERROR, code)
        self.assertIn("No space left", err)
        self.assertNotIn("開けない", err)
        self.assertNotIn("保存済み", err)  # 印は保存されていないのでヒントも付けない

    def test_decide_keeps_the_owner_mark_saved_hint_when_the_ledger_write_fails(self):
        self._ingested()
        with mock.patch(
            "karte.owner_cli.owner_decision.write_karte", side_effect=OSError(errno.ENOSPC, "No space left on device")
        ):
            code, _, err = self._decide(scope="out")
        self.assertEqual(cli.EXIT_ERROR, code)
        self.assertIn("No space left", err)
        self.assertIn("scope のオーナー印は保存済み", err)
        self.assertEqual({f"F-{self.issue}-01": "out"}, scope_ledger.owner_scopes(self.issue, self.root))


if __name__ == "__main__":
    unittest.main()
