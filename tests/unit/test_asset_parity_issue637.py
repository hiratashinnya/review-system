"""Issue #637: misplaced principle files remain visible across exemption states."""

import json
import tempfile
import unittest
from pathlib import Path

from asset_parity.copilot_paths import copilot_prompt_path, copilot_skill_path, inline_slot_path
from asset_parity.inventory import MODE_PRINCIPLE, scan_parity_seeds
from asset_parity.report import build_report, render_json, render_text
from asset_parity.staleness import compare
from tests.unit.test_asset_parity_copilot_paths import _github_path_literal_lines


class TestIssue637(unittest.TestCase):
    def test_misplaced_files_visible_with_or_without_exemption_and_inlining(self):
        for exempt in (None, 'documented non-mirror'):
            for inlined in (False, True):
                with self.subTest(exempt=exempt, inlined=inlined), tempfile.TemporaryDirectory() as tmp:
                    root = Path(tmp)
                    seed = root / '.claude/skills/doctrine/SKILL.md'
                    seed.parent.mkdir(parents=True)
                    seed.write_text('---\nuser-invocable: false\ndisable-model-invocation: true\n---\n')
                    for path in (copilot_skill_path('doctrine', root), copilot_prompt_path('doctrine', root)):
                        path.parent.mkdir(parents=True, exist_ok=True)
                        path.write_text('misplaced')
                    if inlined:
                        (root / '.github/copilot-instructions.md').write_text(
                            'header\n\n<!-- principles-source: .ai/skills/doctrine/SKILL.md; '
                            + 'sha256: ' + '0' * 64 + ' -->\n')
                    self.assertEqual(scan_parity_seeds(root)[0].mode, MODE_PRINCIPLE)
                    report = build_report(root, is_exempt_fn=lambda *args: exempt)
                    cell = report.rows[0].cells['github']
                    self.assertEqual(cell.status, 'exempt' if exempt or inlined else 'missing')
                    assert cell.reason is not None
                    self.assertIn('misplaced files:', cell.reason)
                    for output in (render_text(report), render_json(report)):
                        self.assertIn('.github/skills/doctrine/SKILL.md', output)
                        self.assertIn('.github/prompts/doctrine.prompt.md', output)
                    self.assertEqual(json.loads(render_json(report))['summary']['missing_count'],
                                     report.missing_count)

    def test_virtual_slot_has_windows_safe_filename(self):
        slot = inline_slot_path('doctrine', Path('/repo'))
        self.assertFalse(any(char in slot.name for char in '<>:"/\\|?*'))
        self.assertFalse(slot.is_file(follow_symlinks=False))

    def test_scanner_evaluates_addition_and_handles_case_and_unusual_path_chars(self):
        source = ('a = ".git" + "hub/skills"\n'
                  'b = ".GitHub/@skill"\n'
                  'c = ".github/日本語"\n'
                  'd = "Copilot（.github/）"\n')
        self.assertEqual(_github_path_literal_lines(source), [1, 2, 3])

    def test_compare_rejects_non_path_at_boundary(self):
        with self.assertRaises(TypeError):
            compare('not a Path', Path('/mirror'), Path('/repo'))
