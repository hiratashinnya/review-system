import json

from conflict_repair.runner import evaluate
from maintainability_lint.scanner import build_baseline
from .test_runner import API
from .test_git_repair import RealGitTest, cmd, save


class BaselineSourceMergeTest(RealGitTest):
    def test_independent_module_and_class_updates_against_merged_source(self):
        cmd(self.repo, 'switch', 'main')
        module = self.repo / 'long.py'
        mixed = self.repo / 'mixed.py'
        module.write_text('pass\n' * 101)
        mixed.write_text('from dataclasses import dataclass\n@dataclass\nclass Data:\n    x: int\nclass Logic:\n    def f(self):\n        return 1\n')
        path = self.repo / 'maintainability_lint/baseline.json'
        def snapshot():
            path.write_text(json.dumps(build_baseline(self.repo), sort_keys=True) + '\n')
        snapshot()
        save(self.repo, 'ancestor debt')
        cmd(self.repo, 'branch', '-f', 'feature', 'main')
        cmd(self.repo, 'switch', 'feature')
        mixed.write_text(mixed.read_text().replace('class Data:', 'class OtherData:'))
        snapshot()
        head = save(self.repo, 'update class')
        cmd(self.repo, 'switch', 'main')
        module.write_text('pass\n' * 102)
        snapshot()
        base = save(self.repo, 'update module')
        bare = self.repo.parent / 'remote.git'
        cmd(self.repo.parent, 'clone', '--bare', str(self.repo), str(bare))
        cmd(self.repo, 'remote', 'add', 'origin', str(bare))
        api = API(bare, base, head)
        result = evaluate(api, self.repo, 1, 'owner/repo', 'main')
        self.assertTrue(result['push'])
        merged = json.loads(cmd(bare, 'show', 'feature:maintainability_lint/baseline.json'))
        self.assertEqual(merged['module_lines']['long.py']['line_count'], 102)
        self.assertEqual(merged['mixed_class_files']['mixed.py']['data'], ['OtherData'])
        self.assertEqual(merged['mixed_class_files']['mixed.py']['logic'], ['Logic'])
        head_baseline = json.loads(cmd(bare, 'show', f'{head}:maintainability_lint/baseline.json'))
        self.assertEqual(merged['mixed_class_files']['mixed.py'], head_baseline['mixed_class_files']['mixed.py'])
        self.assertEqual(merged['module_lines']['long.py'], build_baseline(self.repo)['module_lines']['long.py'])
