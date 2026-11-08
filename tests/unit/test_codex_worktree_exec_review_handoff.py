"""Codex pr-reviewer の外側取り込みを model-free の子プロセスで検証する。"""

import contextlib
import io
import json
from pathlib import Path
import shutil
import shlex
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from codex_worktree_exec.cli import EXIT_REFUSED, main
from codex_worktree_exec.errors import CodexExecError
from codex_worktree_exec.review_handoff import _ingest, _save_handoff
from karte import model, paths
from tests.unit.codex_worktree_exec_support import clean_environ, make_repository, write_trust


REPORT = """### F-375-01
harm: real
harm_detail: 検証が素通りする
severity: major
scope: in
evidence: source.py:1 を確認した
locus: source.py::check
summary: 検証が不足している
expected: 不正入力を拒否する
recheck: 不正入力を実行する
"""


class CodexReviewerHandoffTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.primary, self.worktree = make_repository(self.directory)
        root = Path(__file__).resolve().parents[2]
        criteria = (".ai/skills/review-harm/SKILL.md", ".claude/skills/review-harm/SKILL.md")
        for relative in criteria:
            destination = self.worktree / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(root / relative, destination)
        subprocess.run(["git", "-C", str(self.worktree), "add", "--", *criteria], check=True)
        subprocess.run(["git", "-C", str(self.worktree), "-c", "user.name=Test",
                        "-c", "user.email=test@example.invalid", "commit", "-qm", "review criteria"], check=True)
        karte_source = Path(__file__).resolve().parents[2] / "karte"
        for root in (self.primary, self.worktree):
            shutil.copytree(karte_source, root / "karte", ignore=shutil.ignore_patterns("__pycache__"))
        self.home = self.directory / "codex-home"
        write_trust(self.home, self.primary)
        (self.primary / "tmp" / "_karte").mkdir(parents=True)
        (self.primary / "tmp" / "_karte" / "active.json").write_text(
            json.dumps({"issue": 375, "round": 0}), encoding="utf-8"
        )
        (self.worktree / "tmp").mkdir()
        (self.worktree / "tmp" / "prompt.md").write_text("Review the assigned change.", encoding="utf-8")
        self.output = self.worktree / "tmp" / "result.md"
        self.codex = self.directory / "fake-codex"
        self.ingest = patch(
            "codex_worktree_exec.review_handoff._ingest", return_value=(0, "ingested", ())
        )
        self.ingest_mock = self.ingest.start()
        self.addCleanup(self.ingest.stop)
        self.binding = patch("codex_worktree_exec.cli.verify_artifact_binding", return_value=375)
        self.binding_mock = self.binding.start()
        self.addCleanup(self.binding.stop)

    def make_codex(self, *, exit_code=0, content=REPORT, stdout="PRIVATE-OUTPUT",
                   stderr="", pointer_after=None, advance_handoff=None):
        script = (
            "#!/bin/sh\n"
            "out=\n"
            "while [ \"$#\" -gt 0 ]; do\n"
            "  if [ \"$1\" = \"--output-last-message\" ]; then out=\"$2\"; shift 2; else shift; fi\n"
            "done\n"
            + f"cat > \"$out\" <<'REPORT_BODY'\n{content}REPORT_BODY\n"
            + f"printf '%s\\n' '{stdout}'\nexit {exit_code}\n"
        )
        if stderr:
            script = script.replace(
                f"printf '%s\\n' '{stdout}'\n",
                f"printf '%s\\n' '{stdout}'\nprintf '%s\\n' {shlex.quote(stderr)} >&2\n",
            )
        if pointer_after is not None:
            pointer = shlex.quote(str(self.primary / "tmp" / "_karte" / "active.json"))
            content_json = shlex.quote(json.dumps(pointer_after))
            advance = ""
            if advance_handoff is not None:
                advance = (
                    f"cd {shlex.quote(str(self.primary))} && "
                    f"python3 -m karte ingest-reviewer --from {shlex.quote(str(advance_handoff))} >/dev/null\n"
                )
            script = script.replace(
                f"printf '%s\\n' '{stdout}'\n",
                f"printf '%s\\n' '{stdout}'\n{advance}printf '%s' {content_json} > {pointer}\n",
            )
        self.codex.write_text(script, encoding="utf-8")
        self.codex.chmod(0o755)

    def run_main(self, role="pr-reviewer", *, exit_code=0, content=REPORT,
                 stderr="", pointer_after=None, advance_handoff=None):
        self.make_codex(
            exit_code=exit_code, content=content,
            stdout="PRIVATE-OUTPUT" if role == "pr-reviewer" else "",
            stderr=stderr, pointer_after=pointer_after, advance_handoff=advance_handoff,
        )
        argv = [
            "--role", role, "-C", str(self.worktree), "--prompt-file", "tmp/prompt.md",
            "--output-file", "tmp/result.md", "--model", "gpt-6-sol",
            "--reasoning-effort", "high", "--timeout-seconds", "5",
            "--binding-file", "tmp/binding.json",
        ]
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = main(
                argv, environ=clean_environ(CODEX_HOME=str(self.home)),
                cwd=self.worktree, codex=str(self.codex),
            )
        return code, out.getvalue(), err.getvalue()

    def test_success_saves_raw_body_and_imports_without_returning_full_text(self):
        code, out, err = self.run_main()
        self.assertEqual(0, code, err)
        self.assertEqual("", err)
        self.assertIn("tmp/_handoff/pr-reviewer--", out)
        self.assertIn("取り込み済み", out)
        self.assertNotIn("検証が不足", out)
        self.assertEqual(1, len(out.splitlines()))
        self.ingest_mock.assert_called_once()
        worktree, handoff = self.ingest_mock.call_args.args
        self.assertEqual(self.worktree, worktree)
        self.assertEqual("<!-- handoff issue=375 round=1 -->\n" + REPORT,
                         handoff.read_text(encoding="utf-8"))

    def test_existing_ingest_reviewer_cli_runs_from_linked_worktree_and_writes_primary_ledger(self):
        handoff = _save_handoff(self.primary, REPORT, 375, 1)
        code, detail, warnings = _ingest(self.worktree, handoff)
        self.assertEqual(0, code, detail)
        self.assertEqual((), warnings)
        karte_path = paths.karte_path(375, self.primary)
        self.assertEqual("F-375-01", model.parse(karte_path.read_text()).findings[0].id)

    def test_ingest_collects_warning_emitted_only_on_stderr(self):
        from types import SimpleNamespace
        warning = "警告: stderr-only diagnostic"
        with patch("codex_worktree_exec.review_handoff.subprocess.run", return_value=SimpleNamespace(
            returncode=0, stderr=warning + "\n", stdout="",
        )):
            _code, _detail, warnings = _ingest(self.worktree, self.output)
        self.assertEqual((warning,), warnings)

    def test_ingest_failure_selects_refusal_and_bullets_not_neighboring_lines(self):
        from types import SimpleNamespace
        refusal = "拒否（fail-close）: レビューレポートの検証に失敗"
        bullets = ("  - 2 行目: harm が不正", "  - 12 行目: severity が不正")
        with patch("codex_worktree_exec.review_handoff.subprocess.run", return_value=SimpleNamespace(
            returncode=4,
            stderr="前の診断\n" + refusal + "\n" + "\n".join(bullets) + "\n後続診断\n",
            stdout="",
        )):
            _code, detail, _warnings = _ingest(self.worktree, self.output)
        self.assertIn(refusal, detail)
        for bullet in bullets:
            self.assertIn(bullet.strip(), detail)
        self.assertNotIn("前の診断", detail)
        self.assertNotIn("後続診断", detail)

    def test_ingest_rejection_detail_caps_lines_and_characters(self):
        from types import SimpleNamespace
        lines = ["拒否（fail-close）: bad"] + [f"  - {index}: short" for index in range(20)]
        with patch("codex_worktree_exec.review_handoff.subprocess.run", return_value=SimpleNamespace(
            returncode=4, stderr="\n".join(lines), stdout="",
        )):
            _code, detail, _warnings = _ingest(self.worktree, self.output)
        self.assertLessEqual(len(detail), 1000)
        self.assertLessEqual(len(detail.splitlines()), 8)
        self.assertIn("…ほか 14 件", detail)

    def test_rejection_detail_does_not_omit_eight_lines_or_omit_after_nine(self):
        from codex_worktree_exec.ingest_diagnostics import rejection_detail
        heading = "拒否（fail-close）: bad"
        exactly_eight = [heading] + [f"  - detail {index}" for index in range(7)]
        result = rejection_detail(exactly_eight, [0])
        self.assertEqual(8, len(result.splitlines()))
        self.assertNotIn("…ほか", result)
        self.assertEqual("detail 6", result.splitlines()[-1].removeprefix("- "))

        nine = [heading] + [f"  - detail {index}" for index in range(8)]
        result = rejection_detail(nine, [0])
        self.assertEqual(8, len(result.splitlines()))
        self.assertIn("…ほか 2 件", result)

    def test_rejection_detail_stops_bullets_at_the_next_non_bullet_line(self):
        from codex_worktree_exec.ingest_diagnostics import rejection_detail
        lines = ["拒否: a", "  - x", "警告: w", "  - wb"]
        detail = rejection_detail(lines, [0])
        self.assertIn("- x", detail)
        self.assertNotIn("- wb", detail)

    def test_rejection_detail_caps_multiple_four_line_refusals(self):
        from codex_worktree_exec.ingest_diagnostics import rejection_detail
        lines = []
        rejected = []
        for index in range(2):
            rejected.append(len(lines))
            lines.extend([f"拒否 {index}"] + [f"  - {index}.{bullet}" for bullet in range(3)])
        detail = rejection_detail(lines, rejected)
        self.assertLessEqual(len(detail.splitlines()), 8)
        self.assertEqual(8, len(detail.splitlines()))
        self.assertNotIn("…ほか", detail)

        lines.extend(["拒否 2"] + [f"  - 2.{bullet}" for bullet in range(3)])
        rejected.append(8)
        detail = rejection_detail(lines, rejected)
        self.assertLessEqual(len(detail.splitlines()), 8)
        self.assertIn("…ほか 5 件", detail)
        self.assertEqual(5, int(detail.rsplit("…ほか ", 1)[1].split()[0]))

    def test_rejection_detail_keeps_eight_lines_when_exactly_at_character_limit(self):
        from codex_worktree_exec.ingest_diagnostics import rejection_detail
        header = "拒否: " + "h" * 987
        bullet = "  - " + "b" * 6
        detail = rejection_detail([header, bullet], [0])
        self.assertEqual(1000, len(detail))
        self.assertNotIn("…ほか", detail)

    def test_rejection_detail_keeps_all_shown_text_when_suffix_hits_character_limit(self):
        from codex_worktree_exec.ingest_diagnostics import rejection_detail
        heading = "拒否: a"
        short_bullets = ["  - x"] * 5
        suffix = "\n…ほか 1 件"
        long_bullet = "  - " + "r" * (1000 - len(heading) - 5 * 3 - 6 - len(suffix) - 2)
        lines = [heading, *short_bullets, long_bullet, "  - omitted"]
        detail = rejection_detail(lines, [0])
        self.assertEqual(1000, len(detail))
        self.assertEqual(8, len(detail.splitlines()))
        self.assertEqual(long_bullet.strip(), detail.splitlines()[-2])
        self.assertEqual("…ほか 1 件", detail.splitlines()[-1])

    def test_rejection_detail_truncates_long_bullet_under_content_free_heading(self):
        from codex_worktree_exec.ingest_diagnostics import rejection_detail
        detail = rejection_detail(
            ["拒否（fail-close）: レビューレポートの検証に失敗:", "  - 先頭理由: " + "x" * 1200],
            [0],
        )
        self.assertLessEqual(len(detail), 1000)
        self.assertTrue(detail.startswith("拒否（fail-close）: レビューレポートの検証に失敗:\n- 先頭理由:"))
        self.assertTrue(detail.endswith("…"))
        self.assertNotIn("…ほか", detail)

    def test_rejection_detail_truncates_long_bullet_in_later_block(self):
        from codex_worktree_exec.ingest_diagnostics import rejection_detail
        lines = ["拒否: first", "  - short", "拒否: second", "  - long reason " + "x" * 1200]
        detail = rejection_detail(lines, [0, 2])
        self.assertLessEqual(len(detail), 1000)
        self.assertIn("拒否: first\n- short\n拒否: second\n- long reason ", detail)
        self.assertTrue(detail.endswith("…"))
        self.assertNotIn("…ほか", detail)

    def test_rejection_detail_truncates_long_bullet_after_short_bullet(self):
        from codex_worktree_exec.ingest_diagnostics import rejection_detail
        lines = ["拒否: first", "  - short", "  - long reason " + "x" * 1200]
        detail = rejection_detail(lines, [0])
        self.assertLessEqual(len(detail), 1000)
        self.assertTrue(detail.startswith("拒否: first\n- short\n- long reason "))
        self.assertTrue(detail.endswith("…"))
        self.assertNotIn("…ほか", detail)

    def test_ingest_rejection_character_limit_counts_omitted_bullets(self):
        from types import SimpleNamespace
        lines = ["拒否（fail-close）: bad"] + [
            f"  - {index}: {'x' * 300}" for index in range(5)
        ]
        with patch("codex_worktree_exec.review_handoff.subprocess.run", return_value=SimpleNamespace(
            returncode=4, stderr="\n".join(lines), stdout="",
        )):
            _code, detail, _warnings = _ingest(self.worktree, self.output)
        self.assertLessEqual(len(detail), 1000)
        self.assertIn("- 2:", detail)
        self.assertIn("- 3:", detail)
        self.assertNotIn("- 4:", detail)
        self.assertIn("…ほか 1 件", detail)

    def test_ingest_truncates_a_single_oversized_refusal_line(self):
        from types import SimpleNamespace
        line = "拒否（fail-close）: " + "x" * 1200
        with patch("codex_worktree_exec.review_handoff.subprocess.run", return_value=SimpleNamespace(
            returncode=4, stderr=line, stdout="",
        )):
            _code, detail, _warnings = _ingest(self.worktree, self.output)
        self.assertLessEqual(len(detail), 1000)
        self.assertTrue(detail.endswith("…"))

    def test_oversized_first_refusal_keeps_omitted_line_count(self):
        from types import SimpleNamespace
        lines = [
            "拒否（fail-close）: " + "x" * 1200,
            "  - first refusal detail",
            "拒否（fail-close）: second refusal",
            "  - second refusal detail",
        ]
        with patch("codex_worktree_exec.review_handoff.subprocess.run", return_value=SimpleNamespace(
            returncode=4, stderr="\n".join(lines), stdout="",
        )):
            _code, detail, _warnings = _ingest(self.worktree, self.output)
        self.assertLessEqual(len(detail), 1000)
        self.assertLessEqual(len(detail.splitlines()), 8)
        self.assertIn("…ほか 3 件", detail)
        self.assertTrue(detail.splitlines()[0].endswith("…"))

    def test_ingest_failure_without_refusal_returns_last_nonempty_line(self):
        from types import SimpleNamespace
        with patch("codex_worktree_exec.review_handoff.subprocess.run", return_value=SimpleNamespace(
            returncode=1, stderr="Traceback (most recent call last):\n\n  error: first\n\n", stdout="\nfinal error\n",
        )):
            _code, detail, _warnings = _ingest(self.worktree, self.output)
        self.assertEqual("final error", detail)

    def test_main_runs_real_ingest_reviewer_and_rejects_invalid_report_without_mutation(self):
        activated = subprocess.run(
            [sys.executable, "-m", "karte", "activate", "--issue", "375"],
            cwd=self.primary, capture_output=True, text=True, check=False,
        )
        self.assertEqual(0, activated.returncode, activated.stderr)
        self.ingest.stop()
        code, out, err = self.run_main()
        self.assertEqual(0, code, err)
        self.assertIn("取り込み済み", out)
        self.assertEqual("F-375-01", model.parse(paths.karte_path(375, self.primary).read_text()).findings[0].id)
        handoffs = list((self.primary / "tmp" / "_handoff").glob("pr-reviewer--*.md"))
        self.assertEqual(1, len(handoffs))
        self.assertTrue(handoffs[0].is_relative_to(self.primary / "tmp" / "_handoff"))

        before = paths.karte_path(375, self.primary).read_bytes()
        self.output.unlink()
        code, _out, err = self.run_main(content="レビュー本文だが finding block は無い\n")
        self.assertEqual(EXIT_REFUSED, code)
        self.assertIn("CODEX_REVIEW_INGEST_FAILED", err)
        self.assertEqual(before, paths.karte_path(375, self.primary).read_bytes())
        self.assertIn("拒否（fail-close）:", err)

    def test_real_ingest_warnings_are_returned_once(self):
        activated = subprocess.run(
            [sys.executable, "-m", "karte", "activate", "--issue", "375"],
            cwd=self.primary, capture_output=True, text=True, check=False,
        )
        self.assertEqual(0, activated.returncode, activated.stderr)
        self.ingest.stop()
        second = REPORT.replace("F-375-01", "F-375-02").replace(
            "検証が不足している", "別の検証が不足している"
        ).replace("source.py::check", "other.py::check")
        first = _save_handoff(self.primary, REPORT + "\n" + second, 375, 1)
        code, detail, _warnings = _ingest(self.worktree, first)
        self.assertEqual(0, code, detail)
        decided = subprocess.run(
            [sys.executable, "-m", "karte", "decide", "--finding", "F-375-01",
             "--disposition", "deferred", "--deferred-to", "#900", "--scope", "out"],
            cwd=self.primary, capture_output=True, text=True, check=False,
        )
        self.assertEqual(0, decided.returncode, decided.stderr)
        changed = REPORT.replace(
            "recheck: 不正入力を実行する",
            "recheck: 不正入力を実行する\ndisposition: waived",
        )
        code, out, err = self.run_main(content=changed)
        self.assertEqual(0, code, err)
        self.assertEqual(1, out.count("オーナー専権の disposition を無視"))
        self.assertEqual(1, out.count("オーナーが確定した scope を保持"))
        self.assertEqual(1, out.count("再掲されなかった未解消 finding を引き継ぎ"))

    def test_real_ingest_rejection_returns_validation_bullets(self):
        activated = subprocess.run(
            [sys.executable, "-m", "karte", "activate", "--issue", "375"],
            cwd=self.primary, capture_output=True, text=True, check=False,
        )
        self.assertEqual(0, activated.returncode, activated.stderr)
        self.ingest.stop()
        invalid = REPORT.replace("F-375-01", "F-375-20") + "\n" + REPORT.replace(
            "F-375-01", "F-375-21"
        )
        code, _out, err = self.run_main(content=invalid)
        self.assertEqual(EXIT_REFUSED, code)
        self.assertIn("拒否（fail-close）:", err)
        self.assertIn("F-375-20", err)
        self.assertIn("F-375-21", err)
        self.assertGreaterEqual(err.count("拒否（fail-close）:"), 2)

    def test_pointer_issue_change_after_codex_start_fails_closed_before_handoff(self):
        code, out, err = self.run_main(pointer_after={"issue": 901, "round": 0})
        self.assertEqual(EXIT_REFUSED, code)
        self.assertIn("CODEX_REVIEW_INGEST_FAILED", err)
        self.assertNotIn("取り込み済み", out)
        self.ingest_mock.assert_not_called()
        self.assertFalse((self.primary / "tmp" / "_handoff").exists())

    def test_pointer_round_change_after_codex_start_fails_before_handoff(self):
        advanced = _save_handoff(self.primary, REPORT, 375, 1)
        handoff_count = len(list((self.primary / "tmp" / "_handoff").glob("pr-reviewer--*.md")))
        code, out, err = self.run_main(
            pointer_after={"issue": 375, "round": 1}, advance_handoff=advanced
        )
        self.assertEqual(EXIT_REFUSED, code)
        self.assertIn("CODEX_REVIEW_INGEST_FAILED", err)
        self.assertNotIn("取り込み済み", out)
        self.ingest_mock.assert_not_called()
        self.assertEqual(
            handoff_count,
            len(list((self.primary / "tmp" / "_handoff").glob("pr-reviewer--*.md"))),
        )

    def test_binding_issue_mismatch_refuses_before_codex_or_handoff(self):
        active = self.primary / "tmp" / "_karte" / "active.json"
        active.write_text(json.dumps({"issue": 901, "round": 0}), encoding="utf-8")
        self.binding_mock.return_value = 375
        with patch("codex_worktree_exec.cli.run_codex") as run_codex:
            code, out, err = self.run_main()
        self.assertEqual(EXIT_REFUSED, code)
        self.assertIn("CODEX_REVIEW_INGEST_FAILED", err)
        run_codex.assert_not_called()
        self.assertFalse((self.primary / "tmp" / "_handoff").exists())

    def test_ingest_issue_mismatch_is_rejected_directly(self):
        from codex_worktree_exec.review_handoff import ingest_codex_output
        (self.primary / "tmp" / "_karte" / "active.json").write_text(
            json.dumps({"issue": 901, "round": 0}), encoding="utf-8"
        )
        self.output.write_text(REPORT, encoding="utf-8")
        with self.assertRaises(CodexExecError) as caught:
            ingest_codex_output(self.worktree, self.output, 375, (901, 0, 1))
        self.assertEqual("CODEX_REVIEW_INGEST_FAILED", caught.exception.error_id)
        self.assertIn("expected.issue", str(caught.exception))

    def test_direct_ingest_requires_expected_issue_argument(self):
        self.output.write_text(REPORT, encoding="utf-8")
        from codex_worktree_exec.review_handoff import ingest_codex_output
        with self.assertRaises(CodexExecError) as caught:
            ingest_codex_output(self.worktree, self.output, None, (375, 0, 1))
        self.assertEqual("CODEX_REVIEW_INGEST_FAILED", caught.exception.error_id)
        self.assertIn("expected.issue", str(caught.exception))

    def test_codex_nonzero_does_not_create_or_ingest_handoff(self):
        code, out, err = self.run_main(exit_code=7)
        self.assertEqual(EXIT_REFUSED, code)
        self.assertIn("CODEX_REVIEW_CODEX_FAILED", err)
        self.ingest_mock.assert_not_called()
        self.assertFalse((self.primary / "tmp" / "_handoff").exists())

    def test_empty_output_fails_closed(self):
        code, _out, err = self.run_main(content="")
        self.assertEqual(EXIT_REFUSED, code)
        self.assertIn("出力が空", err)
        self.ingest_mock.assert_not_called()

    def test_existing_output_cannot_be_reused_as_a_stale_review(self):
        self.output.write_text(REPORT, encoding="utf-8")
        code, _out, err = self.run_main()
        self.assertEqual(EXIT_REFUSED, code)
        self.assertIn("CODEX_EXEC_OUTPUT_INVALID", err)
        self.ingest_mock.assert_not_called()

    def test_missing_or_stale_progress_pointer_fails_closed(self):
        active = self.primary / "tmp" / "_karte" / "active.json"
        for pointer in (None, {"issue": 375, "round": 1}):
            with self.subTest(pointer=pointer):
                self.ingest_mock.reset_mock()
                self.output.unlink(missing_ok=True)
                if pointer is None:
                    active.unlink(missing_ok=True)
                else:
                    active.write_text(json.dumps(pointer), encoding="utf-8")
                code, _out, err = self.run_main()
                self.assertEqual(EXIT_REFUSED, code)
                self.assertIn("CODEX_REVIEW_INGEST_FAILED", err)
                self.ingest_mock.assert_not_called()
        self.assertFalse((self.primary / "tmp" / "_handoff").exists())

    def test_output_header_mismatch_is_rejected_before_handoff_or_ingest(self):
        for header in (
            "<!-- handoff issue=123 round=1 -->",
            "<!-- handoff issue=375 round=9 -->",
        ):
            with self.subTest(header=header):
                self.output.unlink(missing_ok=True)
                code, _out, err = self.run_main(content=header + "\n" + REPORT)
                self.assertEqual(EXIT_REFUSED, code)
                self.assertIn("食い違", err)
                self.ingest_mock.assert_not_called()
                self.assertFalse((self.primary / "tmp" / "_handoff").exists())

    def test_ingest_failure_returns_nonzero_and_keeps_handoff_for_inspection(self):
        self.ingest_mock.return_value = (4, "入力形式が不正", ())
        code, out, err = self.run_main()
        self.assertEqual(EXIT_REFUSED, code)
        self.assertIn("CODEX_REVIEW_INGEST_FAILED", err)
        self.assertIn("入力形式が不正", err)
        self.assertIn("pr-reviewer--", err)
        self.ingest_mock.assert_called_once()

    def test_only_warning_lines_return_from_ingest(self):
        warning = "警告: オーナー専権の disposition を無視"
        self.ingest_mock.return_value = (0, "finding body leaked", (warning,))
        code, out, err = self.run_main()
        self.assertEqual(0, code, err)
        self.assertIn(warning, out)
        self.assertNotIn("finding body leaked", out)
        self.assertNotIn("検証が不足", out)

    def test_quiet_reviewer_uses_captured_fds_and_failure_reports_sanitized_stderr_only(self):
        failure_stderr = "\n".join(
            [*(f"line-{number:02d}" for number in range(1, 50)), "\033[31mline-50\033[0m"]
        )
        captured = []
        real_popen = subprocess.Popen

        def recording_popen(*args, **kwargs):
            captured.append(kwargs)
            return real_popen(*args, **kwargs)

        with patch("codex_worktree_exec.launcher.subprocess.Popen", recording_popen):
            code, out, err = self.run_main(exit_code=7, stderr=failure_stderr)
        self.assertEqual(EXIT_REFUSED, code)
        self.assertTrue(captured[-1]["stdout"] is subprocess.PIPE)
        self.assertTrue(captured[-1]["stderr"] is subprocess.PIPE)
        self.assertIn("line-50", err)
        self.assertNotIn("line-01", err)
        self.assertNotIn("\033", err)

    def test_missing_expected_issue_stops_before_codex_or_handoff(self):
        self.binding_mock.return_value = None
        with patch("codex_worktree_exec.cli.run_codex") as run_codex:
            code, out, err = self.run_main()
        self.assertEqual(EXIT_REFUSED, code)
        self.assertIn("CODEX_REVIEW_INGEST_FAILED", err)
        run_codex.assert_not_called()
        self.assertFalse((self.primary / "tmp" / "_handoff").exists())

    def test_non_reviewer_role_does_not_import_and_keeps_existing_output_behavior(self):
        code, _out, _err = self.run_main(role="issue-fixer")
        self.assertEqual(0, code)
        self.ingest_mock.assert_not_called()


if __name__ == "__main__":
    unittest.main()
