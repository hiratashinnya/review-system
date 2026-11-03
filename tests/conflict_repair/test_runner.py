import subprocess
from unittest import mock

from conflict_repair import git
from conflict_repair.runner import evaluate
from .test_git_repair import RealGitTest, cmd, save


class API:
    def __init__(self, bare, base, head):
        self.bare, self.base, self.head = bare, base, head
        self.calls = 0
        self.change = None
        self.dispatched = []

    def pulls(self):
        self.calls += 1
        row = {'number': 1, 'state': 'open',
               'base': {'repo': {'full_name': 'owner/repo'}, 'ref': 'main', 'sha': self.base},
               'head': {'repo': {'full_name': 'owner/repo'}, 'ref': 'feature', 'sha': self.head}}
        if self.calls > 1 and self.change == 'child':
            child = {'number': 2, 'state': 'open', 'base': row['head'], 'head': row['base']}
            return [row, child]
        if self.calls > 1 and self.change == 'head':
            row['head']['sha'] = 'f' * 40
        return [row]

    def default_branch(self):
        return 'main'

    def branch_oid(self, branch):
        return cmd(self.bare, 'rev-parse', f'refs/heads/{branch}')

    def dispatch(self, *args):
        self.dispatched.append(args)


class RunnerTest(RealGitTest):
    def setup_remote(self):
        (self.repo / 'AGENTS.md').write_text('drift\n')
        head = save(self.repo, 'drift')
        cmd(self.repo, 'switch', 'main')
        (self.repo / 'base.txt').write_text('base')
        base = save(self.repo, 'base')
        bare = self.repo.parent / 'remote.git'
        cmd(self.repo.parent, 'clone', '--bare', str(self.repo), str(bare))
        cmd(self.repo, 'remote', 'add', 'origin', str(bare))
        return API(bare, base, head)

    def test_drift_push_and_repeat_noop(self):
        api = self.setup_remote()
        result = evaluate(api, self.repo, 1, 'owner/repo', 'main')
        self.assertTrue(result['push'])
        self.assertEqual(api.dispatched, [('conflict-repair-verify.yml', 'main', result['修復後 OID'])])
        api.head = result['修復後 OID']
        result = evaluate(api, self.repo, 1, 'owner/repo', 'main')
        self.assertFalse(result['push'])

    def test_live_relation_and_oid_changes_prevent_push(self):
        for change in ('child', 'head'):
            with self.subTest(change=change):
                api = self.setup_remote() if change == 'child' else api
                api.calls = 0
                api.change = change
                self.assertFalse(evaluate(api, self.repo, 1, 'owner/repo', 'main')['push'])
                self.assertEqual(api.branch_oid('feature'), api.head)

    def test_push_race_does_not_overwrite(self):
        api = self.setup_remote()
        original = git.push
        def raced(source, repo, branch, expected_oid):
            cmd(self.repo, 'switch', 'feature')
            (self.repo / 'race.txt').write_text('race')
            race = save(self.repo, 'race')
            cmd(self.repo, 'push', 'origin', 'feature')
            with self.assertRaises(RuntimeError):
                original(source, repo, branch, expected_oid)
            self.assertEqual(api.branch_oid('feature'), race)
            raise RuntimeError('race')
        with mock.patch.object(git, 'push', side_effect=raced):
            with self.assertRaisesRegex(RuntimeError, 'race'):
                evaluate(api, self.repo, 1, 'owner/repo', 'main')

    def test_generation_failure_does_not_push(self):
        api = self.setup_remote()
        with mock.patch('conflict_repair.runner.regenerate', side_effect=ValueError('failure')):
            with self.assertRaisesRegex(ValueError, 'failure'):
                evaluate(api, self.repo, 1, 'owner/repo', 'main')
        self.assertEqual(api.branch_oid('feature'), api.head)
