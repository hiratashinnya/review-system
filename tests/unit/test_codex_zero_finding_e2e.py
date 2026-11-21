"""#801: Codex wrapper -> 実 ingest-reviewer のゼロfinding統合テスト。"""

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from codex_worktree_exec.errors import CodexExecError
from codex_worktree_exec.review_handoff import ingest_codex_output
from karte import ac_snapshot_binding, model, paths, review_envelope
from karte.active_pointer import read_active, write_active


class CodexZeroFindingE2E(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        shutil.copytree(Path(__file__).resolve().parents[2] / "karte", self.root / "karte",
                        ignore=shutil.ignore_patterns("__pycache__"))
        (self.root / "tmp").mkdir()
        self.issue = self.root / "tmp" / "issue.md"
        self.issue.write_text("# Example\n\n## Acceptance criteria\n- [ ] behavior verified\n", encoding="utf-8")
        self.rec = ac_snapshot_binding.stage(self.root, 801, 1, self.issue)
        self.envelope = review_envelope.expected_of(
            issue=801, phase="implementation", run_id="run-801", target_key="pr-846",
            snapshot_oid="a" * 40, input_digest="b" * 64,
        )
        write_active(self.root, 801, 0, self.envelope, ac_snapshot=self.rec)
        self.output = self.root / "tmp" / "codex-output.md"

    def body(self):
        return ("## Review Summary\n\n### Summary\n"
                "finding_count: 0\nac_count: 1\nac_snapshot_digest: " + self.rec["digest"]
                + "\n\n### AC 1\nresult: satisfied\nevidence: test passed\n"
                "finding_refs: []\n<!-- review-complete -->\n")

    def test_wrapper_to_real_ingest_accepts_zero_and_records_original(self):
        self.output.write_text(self.body(), encoding="utf-8")
        message = ingest_codex_output(self.root, self.output, 801, (801, 0, 1), self.envelope)
        self.assertIn("取り込み済み", message)
        ledger = model.parse(paths.read_text(paths.karte_path(801, self.root)))
        self.assertEqual([], ledger.findings)
        self.assertEqual([1], [round.number for round in ledger.review_rounds])
        saved = self.root / ledger.review_rounds[0].source
        self.assertIn("Review Summary", saved.read_text(encoding="utf-8"))
        self.assertEqual(read_active(self.root)["round"], 1)

    def test_wrapper_empty_and_wrong_digest_fail_close(self):
        for report in ("", self.body().replace(self.rec["digest"], "f" * 64)):
            with self.subTest(report=report[:18]):
                self.output.write_text(report, encoding="utf-8")
                with self.assertRaises(CodexExecError):
                    ingest_codex_output(self.root, self.output, 801, (801, 0, 1), self.envelope)
                self.assertFalse(paths.karte_path(801, self.root).exists())


if __name__ == "__main__":
    unittest.main()
