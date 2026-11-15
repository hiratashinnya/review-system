"""組込み verb のロック宣言、実際の範囲、競合時の待機を固定する。"""
import contextlib
import io
import threading
import unittest
from unittest import mock

from karte import cli, paths, report_source
from karte.verb_boundary import fail_close
from tests.unit.karte_support import RootedCase, finding, ingest_argv, report_text, writer_lock_is_held

REPORT = report_text(("new", finding("a.py::f", "入力を検査しない")))
APPEND = ["append", "--finding-ids", "F-7-01", "--root-cause", "cause", "--change-kind", "logic", "--targets", "a.py::f"]
DIFF = "diff --git a/a.py b/a.py\n--- a/a.py\n+++ b/a.py\n@@ -1 +1,2 @@ def f():\n+x\n"


class TestCliLockScope(RootedCase):
    def ingest_first(self):
        self.assertEqual(0, self.run_verb(ingest_argv(7, 1), REPORT)[0])

    def probe(self, target, method, call, expected):
        observed = []
        original = getattr(target, method)

        def record(*args, **kwargs):
            observed.append(writer_lock_is_held(self.root))
            return original(*args, **kwargs)

        with mock.patch.object(target, method, side_effect=record):
            self.assertEqual(0, call()[0])
        self.assertTrue(observed)
        self.assertTrue(all(value is expected for value in observed), observed)
        return observed

    def test_lock_declarations_and_prepare_binding(self):
        for name, locked in (("ingest_review", True), ("append", True), ("close_attempt", True),
                             ("render", False), ("check", False), ("status", False)):
            with self.subTest(verb=name):
                self.assertIs(getattr(cli, "cmd_" + name).locked, locked)
        closure = [cell.cell_contents for cell in cli.cmd_ingest_review.__closure__]
        self.assertIn(cli._prepare_ingest, closure)

    def test_ingest_prepares_outside_lock_and_writes_inside(self):
        observed = self.probe(report_source, "read_report", lambda: self.run_verb(ingest_argv(7, 1), REPORT), False)
        self.assertEqual([False], observed)
        self.root.joinpath("tmp/_karte/issue-7.md").unlink()
        self.root.joinpath("tmp/_karte/active.json").unlink()
        self.probe(paths, "write_text_atomic", lambda: self.run_verb(ingest_argv(7, 1), REPORT), True)

    def test_append_and_close_write_inside_lock(self):
        self.ingest_first()
        self.probe(paths, "append_text", lambda: self.run_verb(APPEND), True)
        (self.root / "tmp/diff").write_text(DIFF, encoding="utf-8")
        self.probe(paths, "append_text", lambda: self.run_verb(
            ["close-attempt", "--outcome", "fixed", "--diff-file", "tmp/diff"]), True)

    def test_readers_do_not_lock(self):
        self.ingest_first()
        self.run_verb(APPEND)
        (self.root / "tmp/diff").write_text(DIFF, encoding="utf-8")
        self.run_verb(["close-attempt", "--outcome", "fixed", "--diff-file", "tmp/diff"])
        for verb in ("render", "check", "status"):
            with self.subTest(verb=verb):
                self.probe(paths, "read_text", lambda: self.run_verb([verb]), False)

    def test_unlocked_mutation_is_detected_by_write_probe(self):
        self.ingest_first()
        args = cli.build_parser().parse_args(APPEND)
        args.repo_root = str(self.root)
        mutant = fail_close(locked=False)(cli.cmd_append.__wrapped__)
        observed = []
        original = paths.append_text

        def record(*args, **kwargs):
            observed.append(writer_lock_is_held(self.root))
            return original(*args, **kwargs)

        with mock.patch.object(paths, "append_text", side_effect=record):
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(0, mutant(args))
        self.assertEqual([False], observed)
        with self.assertRaises(AssertionError):
            self.assertTrue(all(observed))

    def test_second_writer_waits_until_lock_is_released(self):
        attempted, entered, finished = threading.Event(), threading.Event(), threading.Event()
        real_flock = paths.writer_lock.__wrapped__.__globals__["fcntl"].flock
        flock_module = paths.writer_lock.__wrapped__.__globals__["fcntl"]
        failures = []

        def tracked_flock(fd, operation):
            if threading.current_thread() is worker and operation == flock_module.LOCK_EX:
                attempted.set()
            return real_flock(fd, operation)

        def run():
            try:
                with paths.writer_lock(self.root):
                    entered.set()
            except BaseException as exc:
                failures.append(exc)
            finally:
                finished.set()

        worker = threading.Thread(target=run, daemon=True)
        with mock.patch.object(flock_module, "flock", side_effect=tracked_flock):
            with paths.writer_lock(self.root):
                worker.start()
                self.assertTrue(attempted.wait(5))
                self.assertFalse(entered.wait(0.1))
                self.assertFalse(finished.is_set())
            self.assertTrue(finished.wait(5))
        worker.join(5)
        self.assertFalse(worker.is_alive())
        self.assertFalse(failures)
        self.assertTrue(entered.is_set())
