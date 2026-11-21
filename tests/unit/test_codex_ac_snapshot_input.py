"""Issue #801: network-free Codex gets trusted AC, rejects tampering."""

import json
import tempfile
import unittest
from pathlib import Path

from codex_worktree_exec.errors import CodexExecError
from codex_worktree_exec.review_ac_input import append_ac_snapshot
from karte import ac_snapshot_binding, paths
from karte.active_pointer import write_active

BODY = "# Test\n## Acceptance criteria\n- [ ] verify X\n- [x] verify Y\n"


class CodexAcInputTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.src = self.root / "tmp" / "issue.md"
        self.src.parent.mkdir(parents=True)
        self.src.write_text(BODY, encoding="utf-8")
        self.rec = ac_snapshot_binding.stage(self.root, 801, 1, self.src)
        write_active(self.root, 801, 0, {"marker": "trusted"}, ac_snapshot=self.rec)

    def test_prompt_contains_all_ac_and_digest(self):
        prompt = append_ac_snapshot("Review PR.", self.root, (801, 0, 1))
        self.assertIn('"ac_snapshot_digest": "' + self.rec["digest"] + '"', prompt)
        self.assertIn('"ac_count": 2', prompt)
        self.assertIn('"number": 1', prompt)
        self.assertIn('"text": "verify Y"', prompt)
        self.assertIn("Review PR.", prompt)

    def test_replaced_snapshot_refused(self):
        archived = self.root / self.rec["source"]
        archived.write_text(BODY.replace("verify X", "changed"), encoding="utf-8")
        with self.assertRaises(CodexExecError):
            append_ac_snapshot("Review PR.", self.root, (801, 0, 1))

    def test_malformed_snapshot_is_refused_as_codex_error(self):
        archived = self.root / self.rec["source"]
        archived.write_text(BODY.replace("verify Y", "verify X"), encoding="utf-8")
        with self.assertRaises(CodexExecError):
            append_ac_snapshot("Review PR.", self.root, (801, 0, 1))

    def test_wrong_pointer_rejected(self):
        write_active(self.root, 801, 1, {"marker": "trusted"}, ac_snapshot=self.rec)
        with self.assertRaises(CodexExecError):
            append_ac_snapshot("Review PR.", self.root, (801, 0, 1))

    def test_legacy_without_snapshot_is_unchanged(self):
        write_active(self.root, 801, 0, {"marker": "trusted"}, legacy_finding_only=True)
        self.assertEqual("Review PR.", append_ac_snapshot("Review PR.", self.root, (801, 0, 1)))

    def test_snapshot_missing_without_explicit_legacy_fails_closed(self):
        write_active(self.root, 801, 0, {"marker": "trusted"})
        with self.assertRaises(CodexExecError):
            append_ac_snapshot("Review PR.", self.root, (801, 0, 1))


if __name__ == "__main__":
    unittest.main()
