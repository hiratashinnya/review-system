import json
import tokenize

from maintainability_lint.scanner import build_baseline
from conflict_repair.runner import evaluate
from .test_runner import API, RunnerTest, cmd, save


class BaselineGitTest(RunnerTest):
    def setup_baseline(self, *, guidance=False, new_debt=False, conflicting=False, payload=False, broken=False):
        cmd(self.repo, 'switch', 'main')
        for name in ('a.py', 'b.py'):
            (self.repo / name).write_text('# one\n# two\n# three\n# four\n')
        self.baseline_path = self.repo / 'maintainability_lint/baseline.json'
        self.baseline_path.parent.mkdir(exist_ok=True)
        self.write_baseline(build_baseline(self.repo))
        save(self.repo, 'baseline')
        cmd(self.repo, 'branch', '-f', 'feature', 'main')
        cmd(self.repo, 'switch', 'feature')
        (self.repo / 'b.py').unlink()
        head_baseline = build_baseline(self.repo)
        if conflicting:
            head_baseline['comment_blocks']['shared.py|' + 'a' * 16] = 1
        self.write_baseline(head_baseline)
        if payload:
            (self.repo / 'payload.py').write_text("raise RuntimeError('PR code executed')\n")
        if broken:
            (self.repo / 'invalid.py').write_text('def broken(:\n')
        if guidance:
            (self.repo / 'AGENTS.md').write_text('head drift\n')
        if new_debt:
            (self.repo / 'new.py').write_text('# one\n# two\n# three\n# four\n')
        head = save(self.repo, 'head')
        cmd(self.repo, 'switch', 'main')
        (self.repo / 'a.py').unlink()
        base_baseline = build_baseline(self.repo)
        if conflicting:
            base_baseline['comment_blocks']['shared.py|' + 'a' * 16] = 2
        self.write_baseline(base_baseline)
        if guidance:
            (self.repo / 'AGENTS.md').write_text('base drift\n')
        base = save(self.repo, 'base')
        bare = self.repo.parent / 'remote.git'
        cmd(self.repo.parent, 'clone', '--bare', str(self.repo), str(bare))
        cmd(self.repo, 'remote', 'add', 'origin', str(bare))
        return API(bare, base, head)

    def write_baseline(self, data):
        self.baseline_path.write_text(json.dumps(data, sort_keys=True) + '\n')

    def test_independent_deletions_and_guidance_push_then_noop(self):
        api = self.setup_baseline(guidance=True)
        result = evaluate(api, self.repo, 1, 'owner/repo', 'main')
        self.assertTrue(result['push'])
        self.assertEqual(len(result['baseline 変更キー']['comment_blocks']['削除']), 1)
        data = json.loads(cmd(api.bare, 'show', 'feature:maintainability_lint/baseline.json'))
        self.assertEqual(data['comment_blocks'], {})
        api.head = result['修復後 OID']
        self.assertFalse(evaluate(api, self.repo, 1, 'owner/repo', 'main')['push'])

    def test_unregistered_debt_does_not_push(self):
        api = self.setup_baseline(new_debt=True)
        with self.assertRaisesRegex(ValueError, '違反集合が不一致') as raised:
            evaluate(api, self.repo, 1, 'owner/repo', 'main')
        report = raised.exception.repair_result
        self.assertEqual((report['base OID'], report['head OID']), (api.base, api.head))
        self.assertEqual(len(report['merge-base OID']), 1)
        self.assertIn('関連 PR', report)
        self.assertEqual(len(report['baseline 変更キー']['comment_blocks']['削除']), 1)
        self.assertFalse(report['push'])
        self.assertEqual(api.branch_oid('feature'), api.head)

    def test_conflicting_key_does_not_push(self):
        api = self.setup_baseline(conflicting=True)
        with self.assertRaisesRegex(ValueError, 'baseline conflict'):
            evaluate(api, self.repo, 1, 'owner/repo', 'main')
        self.assertEqual(api.branch_oid('feature'), api.head)

    def test_pr_python_is_not_executed(self):
        api = self.setup_baseline(payload=True)
        self.assertTrue(evaluate(api, self.repo, 1, 'owner/repo', 'main')['push'])

    def test_guidance_conflict_with_unchanged_baseline_and_new_debt_stops(self):
        api = self.setup_remote()
        cmd(self.repo, 'switch', 'feature')
        (self.repo / 'new.py').write_text('# one\n# two\n# three\n# four\n')
        api.head = save(self.repo, 'unregistered debt')
        cmd(self.repo, 'push', 'origin', 'feature')
        with self.assertRaisesRegex(ValueError, '違反集合が不一致') as raised:
            evaluate(api, self.repo, 1, 'owner/repo', 'main')
        report = raised.exception.repair_result
        self.assertEqual((report['base OID'], report['head OID']), (api.base, api.head))
        self.assertEqual(len(report['merge-base OID']), 1)
        self.assertIn('関連 PR', report)
        for section in ('module_lines', 'comment_blocks', 'mixed_class_files'):
            self.assertEqual(report['baseline 変更キー'][section], {'追加': [], '更新': [], '削除': []})
        self.assertFalse(report['push'])
        self.assertEqual(api.branch_oid('feature'), api.head)

    def test_baseline_only_repair(self):
        api = self.setup_baseline()
        self.assertTrue(evaluate(api, self.repo, 1, 'owner/repo', 'main')['push'])

    def test_source_parse_error_does_not_push(self):
        api = self.setup_baseline(broken=True)
        with self.assertRaises((SyntaxError, tokenize.TokenError)):
            evaluate(api, self.repo, 1, 'owner/repo', 'main')
        self.assertEqual(api.branch_oid('feature'), api.head)
