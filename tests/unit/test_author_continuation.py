"""作者専用worktreeへの同branch継承の正常・異常連鎖。"""
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


class AuthorContinuationTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.receipt = self.root / 'tmp/_handoff/collected/author.yaml'
        self.receipt.parent.mkdir(parents=True)
        self.receipt.write_text('status: done\n')
        self.entry = dict(entry_id='wl-previous', issue=371, branch_name='feature/371',
                          agent_type='ac-designer', status='released', closed_at='now',
                          collected_to='tmp/_handoff/collected/author.yaml')
        self.raw = dict(entry_id='wl-previous', receipt_sha256=hashlib.sha256(self.receipt.read_bytes()).hexdigest())
        self.ack = SimpleNamespace(agent_type='change-planner', issue=371, branch_name='feature/371',
                                   expected_oid='a'*40, repository='owner/repo')
        self.runner = lambda *a, **kw: subprocess.CompletedProcess(a, 0, 'a'*40+'\trefs/heads/feature/371\n', '')

    def validate(self, entries=None):
        with patch('issue_start.author_continuation.worktree_ledger.main_worktree_root', return_value=self.root), patch(
            'issue_start.author_continuation.worktree_ledger.read_ledger',
            return_value={'entries': entries or [self.entry]}):
            validate_author_continuation({'prompt': MARKER+json.dumps(self.raw)}, {'prompt_field':'prompt'},
                                         self.ack, self.root, self.runner)

    def test_full_author_chain_accepts_only_released_receipts(self):
        for author, recipient in [('ac-designer','change-planner'), ('change-planner','test-writer'),
                                  ('test-writer','issue-implementer')]:
            self.entry['agent_type'], self.ack.agent_type = author, recipient
            self.validate()

    def test_incomplete_collect_release_and_other_identity_rejected(self):
        for key, value in [('status','running'), ('status','stopped'), ('status','collected'),
                           ('status','release_pending'), ('status','abandoned'), ('closed_at',None),
                           ('issue',372), ('branch_name','other'), ('agent_type','issue-fixer'),
                           ('collected_to',None), ('collected_to','../receipt')]:
            previous = self.entry[key]
            self.entry[key] = value
            with self.subTest(key=key,value=value), self.assertRaises(IssueStartError):
                self.validate()
            self.entry[key] = previous

    def test_changed_missing_receipt_and_stale_owner_rejected(self):
        with self.assertRaises(IssueStartError):
            self.validate([self.entry, {**self.entry, 'entry_id':'new-owner'}])
        self.receipt.write_text('changed')
        with self.assertRaises(IssueStartError):
            self.validate()
        self.receipt.unlink()
        with self.assertRaises(IssueStartError):
            self.validate()

    def test_remote_drift_failure_and_missing_marker_rejected(self):
        for code, output in [(0,'b'*40+'\trefs/heads/feature/371\n'), (1,'')]:
            self.runner = lambda *a, **kw: subprocess.CompletedProcess(a,code,output,'')
            with self.assertRaises(IssueStartError):
                self.validate()
        with self.assertRaises(IssueStartError):
            validate_author_continuation({'prompt':''}, {'prompt_field':'prompt'}, self.ack, self.root)

    def test_existing_fixer_does_not_require_phase_predecessor(self):
        self.ack.agent_type = 'issue-fixer'
        validate_author_continuation({}, {}, self.ack, self.root)

    def test_production_parser_preserves_six_fields_and_requires_release(self):
        from issue_start.gate_dispatch import parse_dispatch_payload
        binding = dict(issue=371, round=2, branch_name=self.ack.branch_name, repository='owner/repo',
                       expected_oid=self.ack.expected_oid, handoff_path='tmp/_handoff/change-planner--issue-371.yaml')
        prompt = 'ISSUE_PHASE_BINDING_V1='+json.dumps(binding)+'\nISSUE_PHASE_INPUT_V1={}\n'+MARKER+json.dumps(self.raw)
        payload = dict(tool_name='Agent', tool_input=dict(subagent_type='change-planner',
                                                        isolation='worktree', prompt=prompt))
        with patch('issue_start.gate_isolation_dispatch.validate_phase_dispatch'):
            with patch('issue_start.author_continuation.worktree_ledger.main_worktree_root', return_value=self.root), patch(
                'issue_start.author_continuation.worktree_ledger.read_ledger', return_value={'entries':[self.entry]}):
                ack = parse_dispatch_payload(payload, cwd=self.root, runner=self.runner)
                self.assertEqual((ack.branch_name, ack.expected_oid), (binding['branch_name'], binding['expected_oid']))
                self.entry['status'] = 'running'
                with self.assertRaisesRegex(IssueStartError, 'CONTINUATION_INVALID'):
                    parse_dispatch_payload(payload, cwd=self.root, runner=self.runner)

    def test_fixer_to_independent_pr_reviewer_remains_readonly_available(self):
        from issue_start.gate_dispatch import parse_dispatch_payload
        from issue_start.readonly_phase_ack import ReadOnlyPhaseAck
        payload = dict(tool_name='Agent', tool_input=dict(subagent_type='pr-reviewer',
                       prompt='ISSUE_PHASE_INPUT_V1='+json.dumps({'binding_file':'b','approval_file':'a'})))
        with patch('issue_start.readonly_phase_dispatch.validate_phase_dispatch') as validate:
            self.assertIsInstance(parse_dispatch_payload(payload, cwd=self.root), ReadOnlyPhaseAck)
            validate.assert_called_once()
