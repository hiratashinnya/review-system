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

    def add_head_commit(self, api, mutate):
        cmd(self.repo, 'switch', 'feature')
        mutate()
        api.head = save(self.repo, 'head variation')
        cmd(self.repo, 'push', 'origin', 'feature')

    def test_stale_registration_in_combined_merge_stops(self):
        api = self.setup_baseline(guidance=True)
        def stale():
            data = json.loads(self.baseline_path.read_text())
            data['comment_blocks']['missing.py|' + 'a' * 16] = 1
            self.write_baseline(data)
        self.add_head_commit(api, stale)
        with self.assertRaisesRegex(ValueError, '違反集合が不一致'):
            evaluate(api, self.repo, 1, 'owner/repo', 'main')
        self.assertEqual(api.branch_oid('feature'), api.head)

    def test_wrong_fingerprint_in_combined_merge_stops(self):
        api = self.setup_baseline(guidance=True)
        def wrong_fingerprint():
            (self.repo / 'long.py').write_text('pass\n' * 101)
            data = json.loads(self.baseline_path.read_text())
            data['module_lines']['long.py'] = {'line_count': 101, 'sha256': 'a' * 64}
            self.write_baseline(data)
        self.add_head_commit(api, wrong_fingerprint)
        with self.assertRaisesRegex(ValueError, '違反集合が不一致'):
            evaluate(api, self.repo, 1, 'owner/repo', 'main')
        self.assertEqual(api.branch_oid('feature'), api.head)

    def test_unregistered_conflict_with_baseline_does_not_push(self):
        api = self.setup_baseline()
        self.add_head_commit(api, lambda: (self.repo / 'other.txt').write_text('head\n'))
        cmd(self.repo, 'switch', 'main')
        (self.repo / 'other.txt').write_text('main\n')
        api.base = save(self.repo, 'base conflict')
        cmd(self.repo, 'push', 'origin', 'main')
        with self.assertRaisesRegex(ValueError, '登録外の競合'):
            evaluate(api, self.repo, 1, 'owner/repo', 'main')
        self.assertEqual(api.branch_oid('feature'), api.head)

    def test_guidance_source_conflict_with_baseline_does_not_push(self):
        api = self.setup_baseline()
        source = self.repo / '.ai/guidance/common.md'
        self.add_head_commit(api, lambda: source.write_text('head\n'))
        cmd(self.repo, 'switch', 'main')
        source.write_text('main\n')
        api.base = save(self.repo, 'source conflict')
        cmd(self.repo, 'push', 'origin', 'main')
        with self.assertRaisesRegex(ValueError, '登録外の競合'):
            evaluate(api, self.repo, 1, 'owner/repo', 'main')
        self.assertEqual(api.branch_oid('feature'), api.head)

    def test_baseline_conflict_with_relation_or_head_race_stops(self):
        api = self.setup_baseline()
        for change in ('child', 'head'):
            with self.subTest(change=change):
                api.change, api.calls = change, 0
                result = evaluate(api, self.repo, 1, 'owner/repo', 'main')
                self.assertFalse(result['push'])
                self.assertEqual(api.branch_oid('feature'), api.head)

    def test_baseline_conflict_with_base_race_stops(self):
        from unittest.mock import patch
        api = self.setup_baseline()
        original = api.branch_oid
        calls = []
        def raced(branch):
            if branch == 'main':
                calls.append(branch)
                if len(calls) > 1:
                    return 'f' * 40
            return original(branch)
        with patch.object(api, 'branch_oid', side_effect=raced):
            result = evaluate(api, self.repo, 1, 'owner/repo', 'main')
        self.assertFalse(result['push'])
        self.assertEqual(original('feature'), api.head)

    def test_repository_hook_does_not_execute_during_baseline_repair(self):
        from unittest.mock import patch
        from conflict_repair import git
        api = self.setup_baseline()
        marker = self.repo.parent / 'hook-ran'
        prepare = git.prepare
        def install_hook(*args):
            result = prepare(*args)
            hook = args[1] / '.git/hooks/pre-commit'
            hook.write_text('#!/bin/sh\ntouch "' + str(marker) + '"\nexit 1\n')
            hook.chmod(0o755)
            return result
        with patch('conflict_repair.runner.git.prepare', side_effect=install_hook):
            self.assertTrue(evaluate(api, self.repo, 1, 'owner/repo', 'main')['push'])
        self.assertFalse(marker.exists())

    def test_comment_count_mismatch_does_not_push(self):
        api = self.setup_baseline()
        def bad_count():
            (self.repo / 'third.py').write_text('# one\n# two\n# three\n# four\n')
            data = json.loads(self.baseline_path.read_text())
            measured = build_baseline(self.repo)['comment_blocks']
            key = next(k for k in measured if k.startswith('third.py|'))
            data['comment_blocks'][key] = 2
            self.write_baseline(data)
        self.add_head_commit(api, bad_count)
        with self.assertRaisesRegex(ValueError, '違反集合が不一致'):
            evaluate(api, self.repo, 1, 'owner/repo', 'main')
        self.assertEqual(api.branch_oid('feature'), api.head)

    def test_mixed_class_fingerprint_mismatch_does_not_push(self):
        api = self.setup_baseline()
        def bad_mixed():
            (self.repo / 'mixed.py').write_text('from dataclasses import dataclass\n@dataclass\nclass Data:\n    x: int\nclass Logic:\n    def f(self):\n        return 1\n')
            data = json.loads(self.baseline_path.read_text())
            data['mixed_class_files']['mixed.py'] = {'data': ['Wrong'], 'logic': ['Logic'], 'sha256': 'a' * 64}
            self.write_baseline(data)
        self.add_head_commit(api, bad_mixed)
        with self.assertRaisesRegex(ValueError, '違反集合が不一致'):
            evaluate(api, self.repo, 1, 'owner/repo', 'main')
        self.assertEqual(api.branch_oid('feature'), api.head)

    def test_deleted_registration_versus_update_does_not_push(self):
        api = self.setup_baseline()
        def update():
            data = json.loads(self.baseline_path.read_text())
            key = next(k for k in data['comment_blocks'] if k.startswith('a.py|'))
            data['comment_blocks'][key] = 2
            self.write_baseline(data)
        self.add_head_commit(api, update)
        with self.assertRaisesRegex(ValueError, 'baseline conflict'):
            evaluate(api, self.repo, 1, 'owner/repo', 'main')
        self.assertEqual(api.branch_oid('feature'), api.head)

    def test_corrupt_baseline_does_not_push(self):
        api = self.setup_baseline()
        self.add_head_commit(api, lambda: self.baseline_path.write_text('{not json}\n'))
        with self.assertRaisesRegex(ValueError, 'invalid baseline JSON'):
            evaluate(api, self.repo, 1, 'owner/repo', 'main')
        self.assertEqual(api.branch_oid('feature'), api.head)

    def test_baseline_conflict_with_close_fork_or_retarget_stops(self):
        from unittest.mock import patch
        api = self.setup_baseline()
        original = api.pulls
        for change in ('close', 'fork', 'retarget'):
            with self.subTest(change=change):
                api.calls = 0
                def altered():
                    rows = original()
                    if api.calls > 1:
                        if change == 'close':
                            return []
                        if change == 'fork':
                            rows[0]['head']['repo']['full_name'] = 'fork/repo'
                        if change == 'retarget':
                            rows[0]['base']['ref'] = 'other'
                    return rows
                with patch.object(api, 'pulls', side_effect=altered):
                    result = evaluate(api, self.repo, 1, 'owner/repo', 'main')
                self.assertFalse(result['push'])
                self.assertEqual(api.branch_oid('feature'), api.head)

    def test_baseline_conflict_with_push_race_does_not_overwrite(self):
        from unittest.mock import patch
        from conflict_repair import git
        api = self.setup_baseline()
        push = git.push
        def raced(source, repo, branch, expected):
            cmd(self.repo, 'switch', 'feature')
            (self.repo / 'race.txt').write_text('race\n')
            race = save(self.repo, 'concurrent update')
            cmd(self.repo, 'push', 'origin', 'feature')
            with self.assertRaises(RuntimeError):
                push(source, repo, branch, expected)
            self.assertEqual(api.branch_oid('feature'), race)
            raise RuntimeError('race detected')
        with patch('conflict_repair.runner.git.push', side_effect=raced):
            with self.assertRaisesRegex(RuntimeError, 'race detected'):
                evaluate(api, self.repo, 1, 'owner/repo', 'main')

    def test_actions_summary_records_success_and_dispatch(self):
        import os
        from unittest.mock import patch
        from conflict_repair.__main__ import main
        api = self.setup_baseline()
        summary = self.repo.parent / 'summary.md'
        env = {'GITHUB_REPOSITORY': 'owner/repo', 'GITHUB_REF': 'refs/heads/main',
               'GITHUB_WORKSPACE': str(self.repo), 'GITHUB_STEP_SUMMARY': str(summary),
               'INPUT_PR_NUMBER': '1'}
        with patch.dict(os.environ, env), patch('conflict_repair.__main__.GitHub', return_value=api):
            main()
        text = summary.read_text()
        for item in ('"pr": 1', '単独/stacked 判定', '関連 PR', 'baseline 変更キー',
                     'merge-base OID', api.base, api.head, '修復後 OID', '"push": true',
                     '検証 dispatch', '未検証'):
            self.assertIn(item, text)
        self.assertEqual(len(api.dispatched), 1)

    def test_actions_summary_records_validation_failure(self):
        import os
        from unittest.mock import patch
        from conflict_repair.__main__ import main
        api = self.setup_baseline(new_debt=True)
        summary = self.repo.parent / 'summary.md'
        env = {'GITHUB_REPOSITORY': 'owner/repo', 'GITHUB_REF': 'refs/heads/main',
               'GITHUB_WORKSPACE': str(self.repo), 'GITHUB_STEP_SUMMARY': str(summary),
               'INPUT_PR_NUMBER': '1'}
        with patch.dict(os.environ, env), patch('conflict_repair.__main__.GitHub', return_value=api):
            main()
        text = summary.read_text()
        for item in ('単独/stacked 判定', '関連 PR', 'baseline 変更キー', 'merge-base OID',
                     api.base, api.head, '違反集合が不一致', '"push": false', '未検証'):
            self.assertIn(item, text)
        self.assertEqual(api.branch_oid('feature'), api.head)

    def test_unknown_source_does_not_push(self):
        api = self.setup_baseline()
        def unknown():
            data = json.loads(self.baseline_path.read_text())
            data['source'] = 'unknown'
            self.write_baseline(data)
        self.add_head_commit(api, unknown)
        with self.assertRaisesRegex(ValueError, 'metadata'):
            evaluate(api, self.repo, 1, 'owner/repo', 'main')
        self.assertEqual(api.branch_oid('feature'), api.head)

    def test_invalid_schema_does_not_push(self):
        api = self.setup_baseline()
        def invalid():
            data = json.loads(self.baseline_path.read_text())
            data['schema_version'] = 3
            self.write_baseline(data)
        self.add_head_commit(api, invalid)
        with self.assertRaisesRegex(ValueError, 'metadata'):
            evaluate(api, self.repo, 1, 'owner/repo', 'main')
        self.assertEqual(api.branch_oid('feature'), api.head)

    def summary_result(self, api):
        import os
        from unittest.mock import patch
        from conflict_repair.__main__ import main
        summary = self.repo.parent / 'summary.md'
        env = {'GITHUB_REPOSITORY': 'owner/repo', 'GITHUB_REF': 'refs/heads/main',
               'GITHUB_WORKSPACE': str(self.repo), 'GITHUB_STEP_SUMMARY': str(summary),
               'INPUT_PR_NUMBER': '1'}
        with patch.dict(os.environ, env), patch('conflict_repair.__main__.GitHub', return_value=api):
            main()
        row = next(line[2:] for line in summary.read_text().splitlines() if line.startswith('- '))
        return json.loads(row)

    def test_conflict_summary_records_both_sides_and_conflicting_key(self):
        api = self.setup_baseline(conflicting=True)
        report = self.summary_result(api)
        evidence = report['baseline 3版の証跡']
        key = 'shared.py|' + 'a' * 16
        self.assertEqual(evidence['状態'], '未統合')
        self.assertEqual(evidence['競合キー']['comment_blocks'], [key])
        for side in ('main', 'head'):
            changes = evidence['各版の変更キー'][side]['comment_blocks']
            self.assertIn(key, changes['追加'])
            self.assertEqual(len(changes['削除']), 1)
        self.assertFalse(report['push'])
        self.assertEqual(api.branch_oid('feature'), api.head)

    def test_corrupt_summary_retains_valid_side_and_marks_unavailable(self):
        api = self.setup_baseline()
        self.add_head_commit(api, lambda: self.baseline_path.write_text('{not json}\n'))
        report = self.summary_result(api)
        evidence = report['baseline 3版の証跡']
        self.assertEqual(evidence['状態'], '未統合')
        self.assertIn('head', evidence['解析エラー'])
        self.assertIsNone(evidence['各版の変更キー']['head'])
        self.assertIsNone(evidence['競合キー'])
        self.assertEqual(len(evidence['各版の変更キー']['main']['comment_blocks']['削除']), 1)
        self.assertFalse(report['push'])
        self.assertEqual(api.branch_oid('feature'), api.head)

    def test_non_utf8_summary_retains_valid_side_and_marks_invalid(self):
        api = self.setup_baseline()
        self.add_head_commit(api, lambda: self.baseline_path.write_bytes(b'\xff\xfe\xff'))
        report = self.summary_result(api)
        evidence = report['baseline 3版の証跡']
        self.assertEqual(evidence['状態'], '未統合')
        self.assertIn('head', evidence['解析エラー'])
        self.assertIsNone(evidence['各版の変更キー']['head'])
        self.assertIsNone(evidence['競合キー'])
        self.assertEqual(len(evidence['各版の変更キー']['main']['comment_blocks']['削除']), 1)
        self.assertFalse(report['push'])
        self.assertEqual(api.branch_oid('feature'), api.head)
