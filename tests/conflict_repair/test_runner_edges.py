from unittest import mock

from conflict_repair.runner import evaluate
from .test_runner import RunnerTest


class RunnerEdgesTest(RunnerTest):
    def test_retarget_before_push(self):
        api = self.setup_remote()
        original = api.pulls
        def retarget():
            rows = original()
            if api.calls > 1:
                rows[0]['base']['ref'] = 'other'
            return rows
        api.pulls = retarget
        self.assertFalse(evaluate(api, self.repo, 1, 'owner/repo', 'main')['push'])
        self.assertEqual(api.branch_oid('feature'), api.head)

    def test_missing_branch_and_api_error_do_not_push(self):
        api = self.setup_remote()
        for name in ('branch_oid', 'pulls'):
            with self.subTest(name=name), mock.patch.object(api, name, side_effect=RuntimeError('unavailable')):
                with self.assertRaisesRegex(RuntimeError, 'unavailable'):
                    evaluate(api, self.repo, 1, 'owner/repo', 'main')
            self.assertEqual(api.branch_oid('feature'), api.head)
