"""TEMPORARY (issue #344 CI-evidence step): intentionally-failing smoke test.

Pushed on purpose to observe the new `.github/workflows/tests.yml` PR check turn
red, per the issue's acceptance criterion that a failing PR must show the check
as `failure`. Removed in the very next commit on this same PR.
"""

import unittest


class CiGateSmokeTest(unittest.TestCase):
    def test_intentional_failure_for_ci_evidence(self):
        self.fail("intentional failure — issue #344 CI red-check evidence, will be reverted next commit")
