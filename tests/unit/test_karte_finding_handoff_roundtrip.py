"""往復検査の削除変異を検出する。"""
import hashlib
import json
from dataclasses import replace
from unittest import mock

from karte.errors import KarteUsageError
from karte.exit_codes import EXIT_ERROR
from karte.finding_handoff_block import END, START, render_block
from karte.finding_handoff_hash import content_hash
from karte.finding_handoff_preview import preview
from tests.unit.test_karte_finding_handoff_predicate import verified_item
from tests.unit.test_karte_finding_handoff_verb_support import VerbCase


class HandoffRoundTripTest(VerbCase):
    def test_roundtrip(self):
        item = verified_item()
        self.assertTrue(preview(item, "Owner/Repo#9", "Codex")[1].startswith("sha256:"))
        for changes in ({"summary": "要約 " + END}, {"summary": "要約 " + START},
                        {"expected": "期待 " + END}, {"locus": ["a,b.py"]}):
            with self.subTest(changes=changes), self.assertRaisesRegex(KarteUsageError, "往復できません"):
                preview(replace(item, **changes), "Owner/Repo#9", "Codex")

    def test_preview_rejects_before_gh(self):
        self.save(replace(verified_item(), summary="要約 " + END, handoff=None))
        with mock.patch("subprocess.run", side_effect=self.run_process) as run:
            code, output, err = self.call("handoff-preview", *self.flags())
        self.assertEqual(EXIT_ERROR, code)
        self.assertIn("往復できません", err)
        self.assertNotIn("確認トークン", output)
        self.assertFalse(any(call.args[0][0] == "gh" for call in run.call_args_list))

    def test_post_rejects_before_gh(self):
        item = replace(verified_item(), summary="要約 " + END, handoff=None)
        self.save(item)
        body = render_block(item, "Codex")
        digest = content_hash(item.id, item.harm, item.summary, item.locus, item.expected)
        data = json.dumps([body, "Owner/Repo#9", "Codex", digest], ensure_ascii=False, separators=(",", ":"))
        token = "sha256:" + hashlib.sha256(data.encode("utf-8")).hexdigest()
        with mock.patch("subprocess.run", side_effect=self.run_process) as run:
            code, _, err = self.call("handoff-post", *self.flags(), "--confirm", token)
            self.assertEqual(0, self.posts)
            self.assertEqual([], self.comments)
            self.assertFalse(any(call.args[0][0] == "gh" for call in run.call_args_list))
            self.assertEqual(EXIT_ERROR, code)
            self.assertIn("往復できません", err)
