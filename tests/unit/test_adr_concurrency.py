"""同時起票の排他と最新状態再読を検証する。"""
import tempfile
import threading
import subprocess
import sys
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from adr.cli_write import file_issue
from adr.store import load, write
from tests.unit.test_adr import draft
from feedback_ledger.tomlwrite import dumps
from adr.schema import ADR_SPEC


class AdrConcurrencyTest(unittest.TestCase):
    def test_parallel_compatible_ids_publish_only_once_in_threads_and_processes(self):
        for topics in (("A", "a"), ("Ａ", "A")):
            for process in (False, True):
                with self.subTest(topics=topics, process=process), tempfile.TemporaryDirectory() as tmp:
                    root, start = Path(tmp) / "adr", threading.Barrier(2)
                    original = __import__("os").link
                    def slow_link(*args):
                        time.sleep(0.1)
                        return original(*args)
                    def compete(topic):
                        start.wait(timeout=5)
                        if process:
                            source = Path(tmp) / (topic + ".draft")
                            source.write_text(dumps(ADR_SPEC, draft(topic)))
                            code = ("import sys,tomllib,time,os; from adr.store import write; "
                                    "link=os.link; os.link=lambda *a:(time.sleep(.1),link(*a))[1]; "
                                    "write(sys.argv[1],tomllib.load(open(sys.argv[2],'rb')))")
                            return subprocess.run([sys.executable, "-c", code, str(root), str(source)],
                                                  capture_output=True, timeout=10).returncode == 0
                        try:
                            write(root, draft(topic))
                            return True
                        except ValueError:
                            return False
                    with patch("adr.store.os.link", side_effect=slow_link), ThreadPoolExecutor(2) as pool:
                        results = list(pool.map(compete, topics))
                    self.assertEqual(sorted(results), [False, True])
                    self.assertEqual(len(load(root)), 1)
                    self.assertEqual(len(list(root.glob("*.toml"))), 1)

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
