"""同時起票の排他と最新状態再読を検証する。"""
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from adr.cli_write import file_issue
from adr.store import load, write
from tests.unit.test_adr import draft


class AdrConcurrencyTest(unittest.TestCase):
    def test_parallel_file_issue_creates_once_and_observes_filed(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "adr"
            write(root, draft())
            entered, release, duplicate = threading.Event(), threading.Event(), threading.Event()
            calls, failures = [], []
            def create(data, repo):
                calls.append(700 + len(calls))
                if len(calls) > 1:
                    duplicate.set()
                entered.set()
                if not release.wait(5):
                    raise RuntimeError("test release timeout")
                return calls[-1], "https://github.com/a/b/issues/700"
            args = SimpleNamespace(root=root, repo=temporary, id=draft()["id"], create=True, issue=None)
            with patch("adr.cli_write.create_issue", side_effect=create), ThreadPoolExecutor(2) as pool:
                first = pool.submit(file_issue, args)
                self.assertTrue(entered.wait(5))
                second = pool.submit(file_issue, args)
                try:
                    self.assertFalse(duplicate.wait(0.1))
                finally:
                    release.set()
                for future in (first, second):
                    try:
                        future.result(timeout=5)
                    except ValueError as exc:
                        failures.append(str(exc))
            self.assertEqual(calls, [700])
            self.assertEqual(len(failures), 1)
            self.assertIn("pending", failures[0])
            self.assertEqual(load(root)[0][0]["decision"]["tracking_issue"], 700)
