"""origin 解析と実行境界。"""

import subprocess
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from karte.finding_handoff_errors import FindingHandoffError
from karte.finding_handoff_origin import get_origin, parse_origin


class OriginTest(unittest.TestCase):
    def test_urls(self):
        for url in ("https://github.com/Owner/Repo.git", "git@github.com:Owner/Repo.git",
                    "ssh://git@GITHUB.COM/Owner/Repo", "https://GITHUB.COM/Owner/Repo"):
            self.assertEqual("Owner/Repo", parse_origin(url))
        for url, kind in (("https://example.com/o/r", "origin_host"), ("git@example.com:o/r", "origin_host"),
                          ("bad", "origin_invalid"), ("https://github.com/o/r/extra", "origin_invalid"),
                          ("ssh://other@github.com/o/r", "origin_invalid")):
            with self.subTest(url=url), self.assertRaises(FindingHandoffError) as error:
                parse_origin(url)
            self.assertEqual(kind, error.exception.kind)

    def test_get_origin(self):
        calls = []
        def run(argv, **kwargs):
            calls.append((argv, kwargs))
            return SimpleNamespace(stdout="git@github.com:Owner/Repo.git\n")
        with patch("subprocess.run", side_effect=AssertionError("実コマンド禁止")):
            self.assertEqual("Owner/Repo", get_origin("/worktree", run))
            self.assertEqual(["git", "remote", "get-url", "origin"], calls[0][0])
            self.assertEqual("/worktree", calls[0][1]["cwd"])
            def missing(*args, **kwargs):
                raise subprocess.CalledProcessError(2, "git")
            with self.assertRaises(FindingHandoffError) as error:
                get_origin("/worktree", missing)
            self.assertEqual("origin_missing", error.exception.kind)
