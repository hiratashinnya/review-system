"""実Git・実parserで旧PR再reviewの適用境界を検証する。"""
import copy
import subprocess
import tempfile
import unittest
from issue_start.gate_support import IssueStartError
from issue_start.readonly_phase_ack import ReadOnlyPhaseAck
from tests.unit.legacy_pr_support import LegacyPrFixture


class LegacyPrRereviewTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.f = LegacyPrFixture(temp.name)
    def test_old_pr_after_development_but_before_real_rollout_is_accepted(self):
        self.f.git('checkout', '-q', 'main')
        before = self.f.git('status', '--porcelain')
        self.assertIsInstance(self.f.parse(), ReadOnlyPhaseAck)
        result, output, evidence = self.f.hook()
        self.assertEqual((result, output), (0, ''))
        self.assertIn('READ_ONLY_PHASE', evidence)
        self.assertEqual(self.f.git('status', '--porcelain'), before)
        self.assertEqual(self.f.git('rev-parse', 'HEAD'), self.f.rollout)
    def test_closed_crossrepo_changed_branch_oid_and_created_after_rollout_rejected(self):
        original = copy.deepcopy(self.f.pr)
        mutations = [dict(state='closed'), dict(merged=True), dict(number=628),
                     dict(created_at='2026-10-21T00:00:00Z'),
                     dict(head=dict(repo=dict(full_name='other/repo'), ref='feature/legacy', sha=self.f.oid)),
                     dict(head=dict(repo=dict(full_name='owner/repo'), ref='other', sha=self.f.oid)),
                     dict(head=dict(repo=dict(full_name='owner/repo'), ref='feature/legacy', sha='b'*40))]
        for change in mutations:
            self.f.pr = {**original, **change}
            with self.subTest(change=change), self.assertRaises(IssueStartError):
                self.f.parse()
    def test_missing_changed_receipt_and_unreleased_or_other_issue_fixer_rejected(self):
        for change in [dict(status='running'), dict(status='release_pending'), dict(closed_at=None),
                       dict(issue=372), dict(agent_type='change-planner')]:
            with self.subTest(change=change), self.assertRaises(IssueStartError):
                self.f.change_ledger(**change)
                self.f.parse()
            self.f.change_ledger(status='released', closed_at='now', issue=371, agent_type='issue-fixer')
        self.f.receipt.write_text('changed')
        with self.assertRaises(IssueStartError):
            self.f.parse()
        self.f.receipt.unlink()
        with self.assertRaises(IssueStartError):
            self.f.parse()
    def test_new_policy_checkout_or_new_phase_author_history_rejected(self):
        self.f.git('checkout', '-q', 'main')
        self.f.raw['expected_oid'] = self.f.rollout
        self.f.pr['head']['sha'] = self.f.rollout
        self.f.git('--git-dir='+str(self.f.remote), 'update-ref', 'refs/heads/feature/legacy', self.f.rollout)
        with self.assertRaisesRegex(IssueStartError, 'new-policy'):
            self.f.parse()
        self.f.git('checkout', '-q', 'feature/legacy')
        self.f.raw['expected_oid'] = self.f.oid
        self.f.pr['head']['sha'] = self.f.oid
        self.f.git('--git-dir='+str(self.f.remote), 'update-ref', 'refs/heads/feature/legacy', self.f.oid)
        self.f.change_ledger(agent_type='ac-designer')
        with self.assertRaisesRegex(IssueStartError, 'phase author'):
            self.f.parse()
    def test_default_without_rollout_or_failed_fetch_rejected(self):
        self.f.git('--git-dir='+str(self.f.remote), 'update-ref', 'refs/heads/main', self.f.old)
        with self.assertRaisesRegex(IssueStartError, 'no observable'):
            self.f.parse()
        def fail(argv, **kwargs):
            if argv[:2] == ['git', 'fetch']:
                return subprocess.CompletedProcess(argv, 1, '', 'offline')
            return self.f.runner(argv, **kwargs)
        with self.assertRaises(IssueStartError):
            self.f.parse(runner=fail)
    def test_role_spoof_mixed_phase_and_untracked_or_modified_source_rejected(self):
        for role, extra in [('adviser',''), ('pr-reviewer','\nISSUE_PHASE_INPUT_V1={}')]:
            with self.subTest(role=role), self.assertRaises(IssueStartError):
                self.f.parse(role=role, extra=extra)
        source = self.f.root / 'unapproved.py'
        source.write_text('unapproved = True\n')
        with self.assertRaisesRegex(IssueStartError, 'untracked source'):
            self.f.parse()
        source.unlink()
        (self.f.root / 'source.py').write_text('dirty = True\n')
        with self.assertRaisesRegex(IssueStartError, 'tracked changes'):
            self.f.parse()
    def test_old_policy_with_phase_artifact_still_requires_normal_approval(self):
        artifact = self.f.root / 'verification_design/VD-371.toml'
        artifact.parent.mkdir()
        artifact.write_text('phase = "verification_design"\n')
        self.f.git('add', str(artifact))
        self.f.git('commit', '-qm', 'new phase artifact')
        oid = self.f.git('rev-parse', 'HEAD')
        self.f.git('push', str(self.f.remote), 'HEAD:refs/heads/feature/legacy')
        self.f.raw['expected_oid'] = self.f.pr['head']['sha'] = oid
        with self.assertRaisesRegex(IssueStartError, 'phase artifacts'):
            self.f.parse()
