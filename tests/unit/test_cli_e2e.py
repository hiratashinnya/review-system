"""TC-cli-001: CLI（version／review→HTML）の通し。FakePlatform で決定化。"""
import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from review_system.io import cli
from review_system.io.report_html import render_html, finding_id_str
from review_system.domain.enums import ApplicationMode
from review_system.domain.ids import RuleId, Location, LineRange, ExecutionId, ContentHash
from review_system.domain.review import Finding, TriagedFinding, UnmatchedFinding, TriageResult
from review_system.domain.report import ReviewReport, ReportSummary, ProvenanceStamp

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
命名が規約に沿っているか。
"""
POLICY = """\
scope: org
version: "1.0"
matrix:
  deterministic:
    "*": auto_fix_log_only
"""


class TestVersionCommand(unittest.TestCase):
    def test_version_prints_constants(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = cli.main(["version"])
        out = buf.getvalue()
        self.assertEqual(rc, 0)
        self.assertIn("review: 3.1", out)
        self.assertIn("criteria MAJOR supported", out)


class TestReviewCommand(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        (self.d / "code.md").write_text(CRITERIA, encoding="utf-8")
        (self.d / "policy.yaml").write_text(POLICY, encoding="utf-8")
        (self.d / "a.py").write_text("uc = 0\n", encoding="utf-8")
        self.out = self.d / "report.html"

    def _run(self, *extra):
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = cli.main([
                "review", str(self.d / "a.py"), "--type", "code",
                "--criteria", str(self.d), "--policy", str(self.d / "policy.yaml"),
                "--out", str(self.out), *extra,
            ])
        return rc, buf.getvalue()

    def test_review_writes_html(self):                   # 配線の通し（空findings でも HTML 生成）
        rc, out = self._run()
        self.assertEqual(rc, 0)
        self.assertTrue(self.out.exists())
        self.assertIn("<!doctype html>", self.out.read_text(encoding="utf-8"))

    def test_review_requires_type(self):                 # 境界：--type 無し→bad request
        rc = cli.main(["review", str(self.d / "a.py"),
                       "--criteria", str(self.d), "--out", str(self.out)])
        self.assertEqual(rc, 2)


class TestHtmlRender(unittest.TestCase):
    def _report(self):
        f = Finding(RuleId("naming-convention"), Location(Path("a.py"), LineRange(1, 1)), "命名が悪い")
        auto = (TriagedFinding(f, ApplicationMode.AUTO_FIX_LOG_ONLY),)
        unc = (UnmatchedFinding("謎の指摘", Location(Path("a.py"))),)
        stamp = ProvenanceStamp(ExecutionId("2026-x"), "fake", "m", "review:3.1", ContentHash("abc"), "now")
        summary = ReportSummary.of(TriageResult(auto, (), (), ()), unc)
        return ReviewReport(auto, (), (), unc, summary, stamp)

    def test_html_embeds_review_id_and_checkboxes(self):  # DD10
        html = render_html(self._report())
        self.assertIn('data-review-id="2026-x"', html)
        self.assertIn("naming-convention@a.py:1-1", html)   # finding id 埋込
        self.assertIn('class="decision"', html)             # チェック入力
        self.assertIn(".feedback.json", html)               # DD14 書き出し


if __name__ == "__main__":
    unittest.main()
