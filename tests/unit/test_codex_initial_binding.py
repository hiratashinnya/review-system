"""工程の初回入力・相談入力はdigest/OID/予算の不一致を拒否する。"""
import hashlib
from pathlib import Path
import tempfile
import unittest
from codex_worktree_exec.initial_binding import validate_initial_binding
from codex_worktree_exec.adviser_request import validate_adviser_request, request_digest
from codex_worktree_exec.adviser_capture import capture_advice, ORIGIN_FIELDS


class InitialBindingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "issue.txt").write_bytes(b"issue")
        self.digest = hashlib.sha256(b"issue").hexdigest()
        self.oid = "a" * 40
        self.initial = dict(recipient="ac-designer", input_file="issue.txt", input_digest=self.digest,
                            snapshot_oid=self.oid, issue=371, run_id="r1", target_key="u1",
                            investigation_reason="原因確定済みのため調査縮小")

    def test_initial_source_digest_and_oid_are_required(self):
        validate_initial_binding(self.initial, "ac-designer", self.root, self.oid)
        for key, value in (("input_digest", "b" * 64), ("snapshot_oid", "b" * 40),
                           ("investigation_reason", ""), ("issue", True)):
            with self.subTest(key=key), self.assertRaises(ValueError):
                validate_initial_binding({**self.initial, key: value}, "ac-designer", self.root, self.oid)
        with self.assertRaises(ValueError):
            validate_initial_binding(self.initial, "issue-implementer", self.root, self.oid)

    def request(self):
        return dict(run_id="r1", issue=371, target_key="u1", caller_role="test-writer",
                    phase="test_design", work_unit="WU-1", max_seconds=60, seconds_used=0, reserve_seconds=10,
                    snapshot_oid=self.oid, model="gpt-6-sol", question="境界条件は？",
                    input_refs=[dict(path="issue.txt", digest=self.digest)],
                    max_calls=1, calls_used=0, max_tokens=1000, tokens_used=0, reserve_tokens=100,
                    max_cost_microusd=1000, cost_used_microusd=0, reserve_cost_microusd=10)

    def test_adviser_input_budget_and_partial_failure(self):
        raw = self.request()
        digest = validate_adviser_request(raw, self.root, self.oid)
        self.assertEqual(digest, request_digest(raw))
        for changes in ({"calls_used": 1}, {"tokens_used": 1000}, {"snapshot_oid": "b" * 40}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                validate_adviser_request({**raw, **changes}, self.root, self.oid)
        answer = dict({key: raw[key] for key in ORIGIN_FIELDS}, request_digest=digest, status="complete", answer="境界を検証")
        metrics = dict(status="success", tokens=20, cost_microusd=2, elapsed_seconds=1)
        result = capture_advice(raw, answer, metrics)
        self.assertEqual(result["adoption"], "pending")
        for response, meter in (({**answer, "status": "partial"}, metrics),
                                 (answer, {**metrics, "status": "failure"}),
                                 (answer, {**metrics, "tokens": 101}),
                                 (answer, {**metrics, "cost_microusd": 11})):
            with self.assertRaises(ValueError):
                capture_advice(raw, response, meter)
