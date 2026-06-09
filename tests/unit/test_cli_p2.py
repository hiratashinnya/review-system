"""TC-cli-002: P2 を CLI で通す（review→🤖適用→feedback→revert）。実 git・FilePlatform。"""
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path

from review_system.io import cli
from review_system.adapters.file_platform import FilePlatformAdapter
from review_system.domain.ids import RuleId

_HAS_GIT = shutil.which("git") is not None

CRITERIA = """\
---
doc_type: code
scope: org
version: "1.0"
rules:
  - id: naming-convention
    title: 命名規則
    severity: error
    determinism: deterministic
    enabled: true
    override: tighten-only
---
## naming-convention — 命名規則
命名規約。
"""
POLICY = "scope: org\nversion: \"1.0\"\nmatrix:\n  deterministic:\n    \"*\": auto_fix_log_only\n"
FINDINGS = {"findings": [{"rule_id": "naming-convention",
                          "location": {"file": "a.py", "line_range": [1, 1]},
                          "rationale": "bad name",
                          "suggested_fix": {"description": "rename", "diff": "user_count = 0\n"}}],
            "unmatched": []}


class TestFilePlatform(unittest.TestCase):
    def test_parses_findings_json(self):
        d = Path(tempfile.mkdtemp())
        (d / "f.json").write_text(json.dumps(FINDINGS), encoding="utf-8")
        resp = FilePlatformAdapter(d / "f.json").review(None, (), ())
        self.assertEqual(resp.findings[0].rule_id, RuleId("naming-convention"))
        self.assertEqual(resp.findings[0].suggested_fix.diff, "user_count = 0\n")


@unittest.skipUnless(_HAS_GIT, "git バイナリが必要（DD5）")
class TestCliP2Flow(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        self.cwd = os.getcwd()
        os.chdir(self.d)
        (self.d / "code.md").write_text(CRITERIA, encoding="utf-8")
        (self.d / "policy.yaml").write_text(POLICY, encoding="utf-8")
        (self.d / "a.py").write_text("uc = 0\n", encoding="utf-8")
        (self.d / "f.json").write_text(json.dumps(FINDINGS), encoding="utf-8")

    def tearDown(self):
        os.chdir(self.cwd)

    def _review(self):
        return cli.main(["review", "a.py", "--type", "code", "--criteria", ".",
                         "--policy", "policy.yaml", "--findings", "f.json", "--out", "report.html"])

    def _ws_file(self):
        rid = cli._review_id_of(Path("report.html"))
        from review_system.domain.ids import ExecutionId
        from review_system.persistence.workspace_git import GitWorkspaceRepository
        return GitWorkspaceRepository(cli.WORKSPACE).workdir(ExecutionId(rid)) / "a.py"

    def test_review_applies_auto(self):                  # 🤖 が適用される
        self.assertEqual(self._review(), 0)
        self.assertTrue(Path("report.html").exists())
        self.assertEqual(self._ws_file().read_text(), "user_count = 0\n")

    def test_feedback_records(self):                     # レポートのパスだけで FB 記録
        self._review()
        rid = cli._review_id_of(Path("report.html"))
        (Path(f"{rid}.feedback.json")).write_text(json.dumps(
            {"review_id": rid, "feedback": [{"finding_id": "naming-convention@a.py:1-1",
                                             "decision": "approve"}]}), encoding="utf-8")
        self.assertEqual(cli.main(["feedback", "report.html"]), 0)
        lines = (cli.STATE / "feedback.jsonl").read_text().splitlines()
        self.assertEqual(len(lines), 1)

    def test_revert_restores(self):                      # レポートのパスだけで revert
        self._review()
        self.assertEqual(cli.main(["revert", "report.html"]), 0)
        self.assertEqual(self._ws_file().read_text(), "uc = 0\n")   # 元へ戻る

    def test_revert_failclose_on_bad_ref(self):          # #10：git 失敗で stack trace せず exit 3
        self._review()
        rid = cli._review_id_of(Path("report.html"))
        cli._commits_path(rid).write_text(json.dumps(["deadbeef"]), encoding="utf-8")
        self.assertEqual(cli.main(["revert", "report.html"]), 3)    # O-14＋EXIT_FAILCLOSE

    def test_revert_failclose_on_corrupt_commits(self):  # #12 T3：壊れた commits.json で fail-close
        self._review()
        rid = cli._review_id_of(Path("report.html"))
        cli._commits_path(rid).write_text("{ not json", encoding="utf-8")
        self.assertEqual(cli.main(["revert", "report.html"]), 3)    # stack trace せず O-14＋exit 3

    def test_feedback_malformed_json(self):              # #6：壊れた入力→fail-close(BADREQ)
        self._review()
        rid = cli._review_id_of(Path("report.html"))
        Path(f"{rid}.feedback.json").write_text("{ not json", encoding="utf-8")
        self.assertEqual(cli.main(["feedback", "report.html"]), 2)

    def test_feedback_review_id_mismatch(self):          # #6：別 review の FB を誤取込しない
        self._review()
        rid = cli._review_id_of(Path("report.html"))
        Path(f"{rid}.feedback.json").write_text(json.dumps(
            {"review_id": "SOMEONE-ELSE", "feedback": []}), encoding="utf-8")
        self.assertEqual(cli.main(["feedback", "report.html"]), 2)

    def test_feedback_missing_keys(self):                # #6/#7：item のキー欠落→BADREQ
        self._review()
        rid = cli._review_id_of(Path("report.html"))
        Path(f"{rid}.feedback.json").write_text(json.dumps(
            {"review_id": rid, "feedback": [{"finding_id": "x"}]}), encoding="utf-8")
        self.assertEqual(cli.main(["feedback", "report.html"]), 2)


if __name__ == "__main__":
    unittest.main()
