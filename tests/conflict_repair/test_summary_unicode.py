import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from conflict_repair.__main__ import main


class SummaryUnicodeTest(unittest.TestCase):
    def test_invalid_unicode_error_does_not_hide_other_results(self):
        class API:
            def default_branch(self):
                return 'main'

            def pulls(self):
                return [{'number': 1}, {'number': 2}]

        with tempfile.TemporaryDirectory() as temp:
            summary = Path(temp) / 'summary'
            env = {'GITHUB_REPOSITORY': 'owner/repo', 'GITHUB_REF': 'refs/heads/main',
                   'GITHUB_WORKSPACE': temp, 'GITHUB_STEP_SUMMARY': str(summary),
                   'INPUT_PR_NUMBER': ''}
            results = [ValueError('invalid \ud800'), {'pr': 2, 'push': False}]
            with patch.dict(os.environ, env), patch('conflict_repair.__main__.GitHub', return_value=API()), \
                    patch('conflict_repair.__main__.evaluate', side_effect=results):
                main()
            rows = [json.loads(line[2:]) for line in summary.read_text().splitlines()
                    if line.startswith('- ')]
            self.assertEqual([row['pr'] for row in rows], [1, 2])
            self.assertFalse(rows[0]['push'])
            self.assertEqual(rows[1], {'pr': 2, 'push': False})
