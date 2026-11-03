"""History completeness and staleness diagnostic regression tests."""

import subprocess
import tempfile
import unittest
from pathlib import Path

from asset_parity.commit_epoch import git_last_commit_epoch
from asset_parity.staleness import compare
from asset_parity.stale_diagnostics import time_direction


class HistoryTests(unittest.TestCase):
    def test_shallow_history_is_unobservable_even_for_a_visible_commit(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / 'source'
            source.mkdir()
            def git(*args):
                subprocess.run(['git', '-C', str(source), *args], check=True,
                               capture_output=True)
            git('init')
            git('config', 'user.email', 'test@example.invalid')
            git('config', 'user.name', 'Test')
            (source / 'a').write_text('first\n')
            git('add', 'a')
            git('commit', '-m', 'first')
            (source / 'a').write_text('second\n')
            git('commit', '-am', 'second')
            clone = root / 'shallow'
            subprocess.run(['git', 'clone', '--depth=1', source.as_uri(), str(clone)],
                           check=True, capture_output=True)
            self.assertIsNotNone(git_last_commit_epoch(source / 'a', source))
            self.assertIsNone(git_last_commit_epoch(clone / 'a', clone))

    def test_directions_and_size_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            seed, mirror = root / 'seed', root / 'mirror'
            seed.write_text('a\n' * 5)
            mirror.write_text('a\n')
            for epochs, expected in [((100, 0), 'parity seed newer'),
                                     ((0, 100), 'mirror newer'),
                                     ((0, 0), 'same time'),
                                     ((None, 0), 'unobservable')]:
                result = compare(seed, mirror, root,
                                 commit_epoch_fn=lambda p, r: epochs[p == mirror])
                self.assertEqual(time_direction(result), expected)
                self.assertEqual(len(result.flag_reasons), 1)
                self.assertIn('size ratio', result.flag_reasons[0])
