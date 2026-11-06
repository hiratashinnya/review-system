"""Tests for resolving live PR merge verification targets."""
import copy
import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from conflict_repair.verification_target import main, resolve


class API:
    repository = 'owner/repo'

    def __init__(self):
        self.base, self.head, self.merge = ('a' * 40, 'b' * 40, 'c' * 40)
        self.pr = {'number': 3, 'state': 'open', 'mergeable': True, 'merge_commit_sha': self.merge,
                   'base': {'ref': 'main', 'repo': {'full_name': self.repository}},
                   'head': {'ref': 'feature', 'sha': self.head, 'repo': {'full_name': self.repository}}}

    def request(self, path):
        return copy.deepcopy(self.pr)

    def default_branch(self):
        return 'main'

    def branch_oid(self, name):
        return self.base if name == 'main' else self.head


class VerificationTargetTests(unittest.TestCase):
    def setUp(self):
        self.api = API()
        self.parents = f'{self.api.merge} {self.api.base} {self.api.head}\n'

    def run_resolve(self):
        with patch('conflict_repair.verification_target.git.run') as run:
            run.return_value = SimpleNamespace(stdout=self.parents)
            return resolve(self.api, '3', self.api.head, '.')

    def test_live_merge_and_parents(self):
        target = self.run_resolve()
        self.assertEqual((target['head_oid'], target['base_oid'], target['merge_oid']),
                         (self.api.head, self.api.base, self.api.merge))

    def test_unavailable_or_changed_pr_fails_closed(self):
        cases = [('state', 'closed'), ('mergeable', None), ('mergeable', False),
                 ('merge_commit_sha', None), ('merge_commit_sha', 'd' * 40)]
        for key, value in cases:
            with self.subTest(key=key, value=value):
                self.api = API()
                self.api.pr[key] = value
                with self.assertRaises(ValueError):
                    self.run_resolve()

    def test_retarget_fork_and_moved_head_fail_closed(self):
        for side, key, value in (('base', 'ref', 'other'), ('head', 'sha', 'd' * 40),
                                 ('head', 'repo', {'full_name': 'fork/repo'})):
            with self.subTest(side=side, key=key):
                self.api = API()
                self.api.pr[side][key] = value
                with self.assertRaises(ValueError):
                    self.run_resolve()

    def test_changed_merge_parents_or_fetch_failure_fail_closed(self):
        for parents in ('c' * 40 + ' ' + 'd' * 40 + ' ' + self.api.head,
                        'c' * 40 + ' ' + self.api.base):
            self.parents = parents
            with self.assertRaises(ValueError):
                self.run_resolve()
        with patch('conflict_repair.verification_target.git.run', side_effect=RuntimeError('fetch')):
            with self.assertRaises(RuntimeError):
                resolve(self.api, '3', self.api.head, '.')

    @patch('conflict_repair.verification_target.GitHub')
    @patch('conflict_repair.verification_target.resolve')
    def test_report_revalidates_the_entire_snapshot(self, mock_resolve, github):
        target = {'number': '3', 'base_ref': 'main', 'base_oid': self.api.base,
                  'head_ref': 'feature', 'head_oid': self.api.head, 'merge_oid': self.api.merge}
        env = {'REPOSITORY': 'owner/repo', 'PR_NUMBER': '3', 'HEAD_OID': self.api.head,
               'TRUSTED_SHA': self.api.base, 'EXPECTED_TARGET': json.dumps(target)}
        mock_resolve.return_value = target
        with patch.dict('os.environ', env, clear=True):
            main()
            mock_resolve.return_value = dict(target, merge_oid='d' * 40)
            with self.assertRaisesRegex(ValueError, 'changed after verification'):
                main()
            mock_resolve.return_value = dict(target, base_oid='d' * 40)
            with self.assertRaisesRegex(ValueError, 'default branch changed'):
                main()

