import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from conflict_repair import git
from conflict_repair.repair import regenerate
from guidance_sync.filesystem import check, render
from guidance_sync.sources import COMMON_SOURCE, PRINCIPLES_SOURCE, TARGETS

ROOT = Path(__file__).resolve().parents[2]


def cmd(repo, *args):
    return subprocess.run(['git', *args], cwd=repo, check=True, text=True,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout.strip()


def save(repo, message):
    cmd(repo, 'add', '.')
    cmd(repo, 'commit', '-m', message)
    return cmd(repo, 'rev-parse', 'HEAD')


class RealGitTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name) / 'repo'
        self.repo.mkdir()
        cmd(self.repo, 'init', '-b', 'main')
        cmd(self.repo, 'config', 'user.name', 'Test')
        cmd(self.repo, 'config', 'user.email', 'test@example.org')
        for path in {COMMON_SOURCE, PRINCIPLES_SOURCE, *TARGETS.values()}:
            dest = self.repo / path
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / path, dest)
        render(self.repo)
        save(self.repo, 'initial')
        cmd(self.repo, 'switch', '-c', 'feature')

    def test_generated_conflict_is_regenerated(self):
        for path in TARGETS:
            with (self.repo / path).open('a') as stream:
                stream.write('head change\n')
        save(self.repo, 'head')
        cmd(self.repo, 'switch', 'main')
        for path in TARGETS:
            with (self.repo / path).open('a') as stream:
                stream.write('base change\n')
        base = save(self.repo, 'base')
        cmd(self.repo, 'switch', 'feature')
        merge = git.run(self.repo, 'merge', '--no-ff', '--no-commit', base, check=False)
        self.assertEqual(git.conflicts(self.repo), set(TARGETS))
        self.assertTrue(regenerate(self.repo, merge))
        self.assertEqual(check(self.repo), [])
        git.commit(self.repo)
        self.assertEqual(len(cmd(self.repo, 'rev-list', '--parents', '-n', '1', 'HEAD').split()), 3)

    def test_source_conflict_rejected(self):
        source = self.repo / COMMON_SOURCE
        source.write_text('head\n')
        save(self.repo, 'head')
        cmd(self.repo, 'switch', 'main')
        source.write_text('base\n')
        base = save(self.repo, 'base')
        cmd(self.repo, 'switch', 'feature')
        merge = git.run(self.repo, 'merge', '--no-ff', '--no-commit', base, check=False)
        with self.assertRaisesRegex(ValueError, '登録外'):
            regenerate(self.repo, merge)

    def test_clean_merge_without_drift_is_noop(self):
        save_path = self.repo / 'feature.txt'
        save_path.write_text('feature')
        save(self.repo, 'head')
        cmd(self.repo, 'switch', 'main')
        (self.repo / 'base.txt').write_text('base')
        base = save(self.repo, 'base')
        cmd(self.repo, 'switch', 'feature')
        merge = git.run(self.repo, 'merge', '--no-ff', '--no-commit', base, check=False)
        self.assertFalse(regenerate(self.repo, merge))
