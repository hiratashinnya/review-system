import hashlib
import tempfile
import unittest
from pathlib import Path

from conflict_repair.governance import governance_status


class GovernanceTest(unittest.TestCase):
    def test_match_mismatch_and_missing_marker(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = ['CLAUDE.md', '.claude/rules/a.md', '.ai/guidance/common.md', '.claude/main-context/a.md']
            digest = hashlib.sha256()
            for path in paths:
                file = root / path
                file.parent.mkdir(parents=True, exist_ok=True)
                file.write_text(path)
                digest.update(path.encode() + b'\0' + path.encode() + b'\0')
            copy = root / '.claude/hooks/governance-directives.md'
            copy.parent.mkdir(parents=True)
            copy.write_text(f'<!-- synced-from: CLAUDE.md@{digest.hexdigest()[:12]} -->')
            self.assertEqual(governance_status(root), '一致')
            (root / paths[0]).write_text('changed')
            self.assertIn('不一致', governance_status(root))
            copy.write_text('no marker')
            self.assertIn('marker なし', governance_status(root))
