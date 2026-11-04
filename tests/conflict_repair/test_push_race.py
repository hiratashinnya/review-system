from unittest import mock

from conflict_repair import git
from conflict_repair.runner import evaluate
from .test_runner import RunnerTest, cmd, save


class PushRaceTest(RunnerTest):
    def test_head_fast_forward_to_base_rejected(self):
        api = self.setup_remote()
        cmd(self.repo, 'switch', 'feature')
        cmd(self.repo, 'switch', '-C', 'descendant')
        (self.repo / 'next.txt').write_text('base advance')
        api.base = save(self.repo, 'base descends head')
        cmd(self.repo, 'push', 'origin', 'descendant:refs/heads/setup')
        cmd(api.bare, 'update-ref', 'refs/heads/main', api.base)
        original = git.push
        def raced(source, repo, branch, expected_oid):
            cmd(self.repo, 'push', 'origin', f'{api.base}:refs/heads/feature')
            return original(source, repo, branch, expected_oid)
        with mock.patch.object(git, 'push', side_effect=raced):
            with self.assertRaises(RuntimeError):
                evaluate(api, self.repo, 1, 'owner/repo', 'main')
        self.assertEqual(api.branch_oid('feature'), api.base)

    def test_rewind_after_revalidation_rejected(self):
        api = self.setup_remote()
        old = cmd(self.repo, 'rev-parse', f'{api.head}^')
        original = git.push
        def raced(source, repo, branch, expected_oid):
            cmd(api.bare, 'update-ref', 'refs/heads/feature', old)
            return original(source, repo, branch, expected_oid)
        with mock.patch.object(git, 'push', side_effect=raced):
            with self.assertRaises(RuntimeError):
                evaluate(api, self.repo, 1, 'owner/repo', 'main')
        self.assertEqual(api.branch_oid('feature'), old)
