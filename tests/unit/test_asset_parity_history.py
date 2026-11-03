"""History completeness and staleness diagnostic regression tests."""

import subprocess
import json
import tempfile
import unittest
from pathlib import Path

from asset_parity.commit_epoch import git_last_commit_epoch
from asset_parity.asset import Asset
from asset_parity.report_model import AssetRow, Cell, Report, STATUS_NA, STATUS_PRESENT
from asset_parity.report_json import render_json
from asset_parity.report_text import render_text
from asset_parity.staleness import compare
from asset_parity.stale_diagnostics import time_direction
from asset_parity.trees import ALL_TREES, GITHUB


class HistoryTests(unittest.TestCase):
    def test_report_directions_and_reasons(self):
        cases = [
            ((40 * 86400, 0), 1, 'parity seed newer', 'last-commit gap 40d > 30d threshold'),
            ((0, 40 * 86400), 1, 'mirror newer', 'last-commit gap 40d > 30d threshold'),
            ((0, 0), 5, 'same time', 'size ratio 5.0x > 2.0x threshold (5 vs 1 lines)'),
        ]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            seed, mirror = root / 'seed', root / 'mirror'
            mirror.write_text('a\n')
            for epochs, seed_lines, direction, reason in cases:
                with self.subTest(direction=direction):
                    seed.write_text('a\n' * seed_lines)
                    signal = compare(seed, mirror, root,
                                     commit_epoch_fn=lambda p, r: epochs[p == mirror])
                    cells = {tree: Cell(STATUS_NA) for tree in ALL_TREES}
                    cells[GITHUB] = Cell(STATUS_PRESENT, mirror, stale=signal)
                    report = Report([AssetRow(Asset('example', 'skill', None, seed), cells)], {})
                    text = render_text(report)
                    stale = json.loads(render_json(report))['assets'][0]['trees'][GITHUB]['stale']
                    self.assertIn(f'example @ .github (Copilot): {direction}', text)
                    self.assertIn(f'example @ .github (Copilot): {reason}', text)
                    self.assertEqual(stale['time_direction'], direction)
                    self.assertEqual(stale['reasons'], [reason])

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
