"""Claudeロール自身の上限で止まった同じroleへの再dispatchを継続検査が通すこと（Issue #829 new-24）。"""
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

RECEIPT = ('schema_version: 1\nagent: {role}\nstatus: {status}\nstop_kind: {kind}\nissue: 371\n'
           'stop_reason: |\n  API Error: 429 rate_limit_error (verbatim)\n')
CONTINUED_ROLES = ('change-planner', 'test-writer', 'issue-implementer')


class ClaudeLimitContinuationTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.relative = 'tmp/_handoff/collected/wl-stopped--change-planner--issue-371-phase.yaml'
        (self.root / self.relative).parent.mkdir(parents=True)
        self.entry = dict(entry_id='wl-stopped', issue=371, branch_name='feature/371', agent_type='change-planner',
                          status='released', closed_at='now', collected_to=self.relative)
        self.ack = SimpleNamespace(agent_type='change-planner', issue=371, branch_name='feature/371',
                                   expected_oid='a'*40, repository='owner/repo')
        self.remote_oid = 'a'*40
        self.write_receipt('change-planner', 'claude-limit')

    def write_receipt(self, role, kind, status='stop', text=None):
        data = (text or RECEIPT.format(role=role, kind=kind, status=status)).encode('utf-8')
        (self.root / self.relative).write_bytes(data)
        self.raw = dict(entry_id='wl-stopped', receipt_sha256=hashlib.sha256(data).hexdigest())

    def runner(self, *args, **_kw):
        return subprocess.CompletedProcess(args, 0, self.remote_oid+'\trefs/heads/feature/371\n', '')

    def validate(self):
        with patch('issue_start.author_continuation.worktree_ledger.main_worktree_root', return_value=self.root), patch(
                'issue_start.author_continuation.worktree_ledger.read_ledger', return_value={'entries': [self.entry]}):
            validate_author_continuation({'prompt': MARKER+json.dumps(self.raw)}, {'prompt_field': 'prompt'},
                                         self.ack, self.root, self.runner)

    def assert_rejected(self):
        with self.assertRaisesRegex(IssueStartError, 'CONTINUATION_INVALID'):
            self.validate()

    def test_same_role_after_claude_limit_accepted(self):
        for role in CONTINUED_ROLES:
            with self.subTest(role=role):
                self.entry['agent_type'] = self.ack.agent_type = role
                self.write_receipt(role, 'claude-limit')
                self.validate()

    def test_codex_limit_on_claude_fixed_role_rejected(self):
        self.write_receipt('change-planner', 'codex-limit')
        self.assert_rejected()

    def test_other_role_or_unreleased_owner_rejected(self):
        for owner, recipient in [('issue-implementer', 'test-writer'), ('issue-fixer', 'issue-implementer'),
                                 ('test-writer', 'change-planner')]:
            with self.subTest(owner=owner, recipient=recipient):
                self.entry['agent_type'], self.ack.agent_type = owner, recipient
                self.write_receipt(owner, 'claude-limit')
                self.assert_rejected()
        self.entry['agent_type'] = self.ack.agent_type = 'test-writer'
        self.write_receipt('test-writer', 'claude-limit')
        for key, value in [('status', 'running'), ('status', 'stopped'), ('status', 'stale'), ('status', 'collected'),
                           ('status', 'abandoned'), ('closed_at', None), ('collected_to', None), ('collected_to', '')]:
            previous = self.entry[key]
            self.entry[key] = value
            with self.subTest(key=key, value=value):
                self.assert_rejected()
            self.entry[key] = previous

    def test_malformed_claude_limit_receipt_rejected(self):
        base = 'schema_version: 1\nagent: change-planner\n'
        for text in [
            base + 'status: stop\nstop_reason: |\n  429\n',
            base + 'status: ready\nstop_kind: claude-limit\nstop_reason: |\n  429\n',
            base + 'status: stop\nstop_kind: claude-limit\nstop_kind: codex-limit\nstop_reason: |\n  429\n',
            base + 'status: stop\nstop_kind: codex-limit\nstop_kind: claude-limit\nstop_reason: |\n  429\n',
            base + 'status: stop\nstop_reason: |\n  stop_kind: claude-limit\n',
            base + 'status: stop\nstop_kind: claude-limit\nstop_reason: "429"\n',
            base + 'status: stop\nstop_kind: claude-limit\nstop_reason: |\n',
            base + 'status: stop\nstop_kind: claude-limit\n',
        ] + [base + f'status: stop\nstop_kind: {kind}\nstop_reason: |\n  429\n'
             for kind in ('claude_limit', 'Claude-limit', 'limit', 'claude-limit codex-limit', '"claude-limit"')]:
            with self.subTest(text=text):
                self.write_receipt('change-planner', '', text=text)
                self.assert_rejected()

    def test_changed_receipt_or_remote_oid_mismatch_rejected(self):
        (self.root / self.relative).write_text(RECEIPT.format(role='change-planner', kind='claude-limit', status='stop')
                                               + 'extra: 1\n')
        self.assert_rejected()
        self.write_receipt('change-planner', 'claude-limit')
        self.remote_oid = 'b'*40
        self.assert_rejected()


if __name__ == '__main__':
    unittest.main()
