"""申し送りの判定・再検証・解析の変異を検出する。"""
from dataclasses import replace
from unittest import mock

from karte import model
from karte.finding_handoff_block import parse_block, render_block
from karte.finding_handoff_exemption import is_stall_exempt
from karte.finding_handoff_hash import content_hash
from tests.unit.test_karte_finding_handoff_predicate import verified_item
from tests.unit.test_karte_finding_handoff_verb_support import VerbCase


class MutationGuardTest(VerbCase):
    def test_real_harm_with_matching_hash_is_not_exempt(self):
        item = replace(verified_item(), harm="real", disposition="deferred", status="open")
        digest = content_hash(item.id, item.harm, item.summary, item.locus, item.expected)
        item.handoff = replace(item.handoff, handoff_content_hash=digest)
        self.assertFalse(is_stall_exempt(item))

    def test_recheck_rejects_other_repository_before_gh(self):
        item = verified_item()
        item.handoff = replace(item.handoff, handoff_issue="Other/Repo#9")
        self.save(item)
        with mock.patch("subprocess.run", side_effect=self.run_process) as run:
            code, output, _ = self.call("handoff-recheck", "--finding", item.id)
        self.assertEqual(4, code)
        self.assertIn("repository", output)
        self.assertEqual("invalid", model.parse(self.path.read_text(encoding="utf-8")).findings[0].handoff.handoff_state)
        self.assertFalse(any(call.args[0][0] == "gh" for call in run.call_args_list))

    def test_agent_line_is_required_and_valid(self):
        body = render_block(verified_item(), "Codex")
        self.assertIsNotNone(parse_block(body))
        lines = body.split("\n")
        for replacement in ("不正", "", "Other (AI) による転記（karte handoff）", None):
            modified = lines[:1] + ([] if replacement is None else [replacement]) + lines[2:]
            with self.subTest(replacement=replacement):
                self.assertIsNone(parse_block("\n".join(modified)))
