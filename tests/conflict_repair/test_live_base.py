from unittest import mock

from conflict_repair import git
from conflict_repair.runner import evaluate
from guidance_sync.filesystem import check
from .test_runner import RunnerTest
from .test_git_repair import cmd


class LiveBaseTest(RunnerTest):
    def test_stale_base_sha_repairs_against_live_base_and_repeats_noop(self):
        api = self.setup_remote()
        api.base = cmd(self.repo, 'rev-parse', 'main^')
        live = api.branch_oid('main')
        result = evaluate(api, self.repo, 1, 'owner/repo', 'main')
        self.assertTrue(result['push'])
        self.assertEqual(result['base OID'], live)
        self.assertEqual(cmd(api.bare, 'show', f"{result['修復後 OID']}:base.txt"), 'base')
        cmd(self.repo, 'fetch', 'origin', 'feature')
        cmd(self.repo, 'switch', '--detach', 'FETCH_HEAD')
        self.assertEqual(check(self.repo), [])
        api.head = result['修復後 OID']
        for _ in range(2):
            result = evaluate(api, self.repo, 1, 'owner/repo', 'main')
            self.assertEqual(result['判定'], '生成物は整合、修復不要')
            self.assertFalse(result['push'])

    def test_only_base_sha_changes_before_push(self):
        api = self.setup_remote()
        original = api.pulls
        def updated():
            rows = original()
            if api.calls > 1:
                rows[0]['base']['sha'] = 'f' * 40
            return rows
        api.pulls = updated
        self.assertTrue(evaluate(api, self.repo, 1, 'owner/repo', 'main')['push'])

    def test_live_changes_fail_closed(self):
        for change in ('close', 'repo', 'base_oid', 'default'):
            with self.subTest(change=change):
                api = self.setup_remote() if change == 'close' else api
                api.calls = 0
                original = API_METHODS['pulls'].__get__(api)
                def altered():
                    rows = original()
                    if api.calls > 1:
                        if change == 'close':
                            return []
                        if change == 'repo':
                            rows[0]['head']['repo']['full_name'] = 'other/repo'
                    return rows
                api.pulls = altered
                api.default_branch = lambda: 'other' if change == 'default' and api.calls > 1 else 'main'
                original_oid = API_METHODS['branch_oid'].__get__(api)
                api.branch_oid = lambda branch: ('f' * 40 if change == 'base_oid' and branch == 'main' and api.calls > 1 else original_oid(branch))
                result = evaluate(api, self.repo, 1, 'owner/repo', 'main')
                self.assertFalse(result['push'])
                self.assertEqual(original_oid('feature'), api.head)

    def test_fetch_mismatch_fails_before_merge(self):
        api = self.setup_remote()
        original = git.run
        def mismatch(repo, *args, **kwargs):
            result = original(repo, *args, **kwargs)
            if args == ('rev-parse', 'FETCH_HEAD^{commit}'):
                result.stdout = 'f' * 40 + '\n'
            return result
        with mock.patch.object(git, 'run', side_effect=mismatch):
            with self.assertRaisesRegex(ValueError, 'fetch OID 不一致'):
                evaluate(api, self.repo, 1, 'owner/repo', 'main')
        self.assertEqual(api.branch_oid('feature'), api.head)


from .test_runner import API
API_METHODS = {'pulls': API.pulls, 'branch_oid': API.branch_oid}
