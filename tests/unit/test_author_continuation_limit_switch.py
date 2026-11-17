"""Codex実行者の上限で止まった同じroleへの再dispatchだけを継続検査が通すこと（Issue #829 new-16）。"""
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from issue_start.author_continuation import MARKER, validate_author_continuation
from issue_start.gate_support import IssueStartError

LIMIT_RECEIPT = ('schema_version: 1\nagent: {role}\nstatus: stop\nstop_kind: codex-limit\nissue: 371\n'
                 'stop_reason: |\n  Codex usage limit reached (verbatim)\n  commit: none\n')


class LimitSwitchContinuationTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.receipt = self.root / 'tmp/_handoff/collected/wl-stopped--test-writer--issue-371-phase.yaml'
        self.receipt.parent.mkdir(parents=True)
        self.entry = dict(entry_id='wl-stopped', issue=371, branch_name='feature/371',
                          agent_type='test-writer', status='released', closed_at='now',
                          collected_to='tmp/_handoff/collected/wl-stopped--test-writer--issue-371-phase.yaml')
        self.ack = SimpleNamespace(agent_type='test-writer', issue=371, branch_name='feature/371',
                                   expected_oid='a'*40, repository='owner/repo')
        self.runner = lambda *a, **_kw: subprocess.CompletedProcess(a, 0, 'a'*40+'\trefs/heads/feature/371\n', '')
        self.write_receipt(LIMIT_RECEIPT.format(role='test-writer'))

    def write_receipt(self, text):
        data = text.encode('utf-8') if isinstance(text, str) else text
        self.receipt.write_bytes(data)
        self.raw = dict(entry_id='wl-stopped', receipt_sha256=hashlib.sha256(data).hexdigest())

    def validate(self):
        with patch('issue_start.author_continuation.worktree_ledger.main_worktree_root', return_value=self.root), patch(
            'issue_start.author_continuation.worktree_ledger.read_ledger', return_value={'entries': [self.entry]}):
            validate_author_continuation({'prompt': MARKER+json.dumps(self.raw)}, {'prompt_field': 'prompt'},
                                         self.ack, self.root, self.runner)

    def assert_rejected(self):
        with self.assertRaisesRegex(IssueStartError, 'CONTINUATION_INVALID'):
            self.validate()

    def test_same_role_after_released_limit_stop_accepted(self):
        for role in ('test-writer', 'issue-implementer'):
            with self.subTest(role=role):
                self.entry['agent_type'] = self.ack.agent_type = role
                self.write_receipt(LIMIT_RECEIPT.format(role=role))
                self.validate()

    def test_claude_fixed_role_and_other_role_rejected(self):
        for owner, recipient in [('change-planner', 'change-planner'), ('issue-implementer', 'test-writer'),
                                 ('issue-fixer', 'issue-implementer')]:
            with self.subTest(owner=owner, recipient=recipient):
                self.entry['agent_type'], self.ack.agent_type = owner, recipient
                self.write_receipt(LIMIT_RECEIPT.format(role=owner))
                self.assert_rejected()

    def test_uncollected_or_unreleased_limit_stop_rejected(self):
        for key, value in [('status', 'running'), ('status', 'stopped'), ('status', 'collected'),
                           ('status', 'release_pending'), ('status', 'abandoned'), ('closed_at', None),
                           ('collected_to', None)]:
            previous = self.entry[key]
            self.entry[key] = value
            with self.subTest(key=key, value=value):
                self.assert_rejected()
            self.entry[key] = previous

    def test_stop_not_caused_by_executor_limit_rejected(self):
        base = 'schema_version: 1\nagent: test-writer\n'
        for text in [
            base + 'status: stop\nstop_reason: |\n  contradiction in plan\n',
            base + 'status: ready\nstop_kind: codex-limit\nstop_reason: |\n  x\n',
            base + 'status: stop\nstop_kind: timeout\nstop_reason: |\n  x\n',
            base + 'status: stop\nstop_kind: codex-limit\nstop_kind: codex-limit\nstop_reason: |\n  x\n',
            base + 'status: stop\nstop_reason: |\n  stop_kind: codex-limit\n',
            base + 'status: stop\nstop_kind: codex-limit\nstop_reason: "limit"\n',
            base + 'status: stop\nstop_kind: codex-limit\n',
        ]:
            with self.subTest(text=text):
                self.write_receipt(text)
                self.assert_rejected()
        self.write_receipt(b'status: stop\nstop_kind: codex-limit\nstop_reason: |\n  \xff\n')
        self.assert_rejected()

    def test_changed_receipt_and_stale_owner_rejected(self):
        self.receipt.write_text(LIMIT_RECEIPT.format(role='test-writer') + 'extra: 1\n')
        self.assert_rejected()
        self.write_receipt(LIMIT_RECEIPT.format(role='test-writer'))
        with patch('issue_start.author_continuation.worktree_ledger.main_worktree_root', return_value=self.root), patch(
            'issue_start.author_continuation.worktree_ledger.read_ledger',
            return_value={'entries': [self.entry, {**self.entry, 'entry_id': 'wl-newer'}]}):
            with self.assertRaisesRegex(IssueStartError, 'CONTINUATION_INVALID'):
                validate_author_continuation({'prompt': MARKER+json.dumps(self.raw)}, {'prompt_field': 'prompt'},
                                             self.ack, self.root, self.runner)

    def test_production_parser_accepts_same_role_limit_switch(self):
        from issue_start.gate_dispatch import parse_dispatch_payload
        from issue_start.gate_support import IsolationOnlyAck
        binding = dict(issue=371, round=2, branch_name='feature/371', repository='owner/repo',
                       expected_oid='a'*40, handoff_path='tmp/_handoff/test-writer--issue-371-phase-switch.yaml')
        prompt = 'ISSUE_PHASE_BINDING_V1='+json.dumps(binding)+'\nISSUE_PHASE_INPUT_V1={}\n'+MARKER+json.dumps(self.raw)
        tool_input: dict[str, str] = dict(subagent_type='test-writer', isolation='worktree', prompt=prompt)
        payload = dict(tool_name='Agent', tool_input=tool_input)
        with patch('issue_start.gate_isolation_dispatch.validate_phase_dispatch', return_value=None):
            with patch('issue_start.author_continuation.worktree_ledger.main_worktree_root', return_value=self.root), patch(
                'issue_start.author_continuation.worktree_ledger.read_ledger', return_value={'entries': [self.entry]}):
                ack = parse_dispatch_payload(payload, cwd=self.root, runner=self.runner)
                self.assertIsInstance(ack, IsolationOnlyAck)
                assert isinstance(ack, IsolationOnlyAck)
                self.assertEqual(ack.agent_type, 'test-writer')
                self.write_receipt('schema_version: 1\nagent: test-writer\nstatus: stop\nstop_reason: |\n  x\n')
                prompt = prompt.rsplit(MARKER, 1)[0] + MARKER + json.dumps(self.raw)
                tool_input['prompt'] = prompt
                with self.assertRaisesRegex(IssueStartError, 'CONTINUATION_INVALID'):
                    parse_dispatch_payload(payload, cwd=self.root, runner=self.runner)
