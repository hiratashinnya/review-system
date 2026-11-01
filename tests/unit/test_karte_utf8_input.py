"""不正な UTF-8 の入力は、traceback（終了コード 1）ではなく fail-close（終了コード 4）に収める（F-696-13）。

``UnicodeDecodeError`` は ``ValueError`` 系で、文書化された終了コード {0,2,3,4} の境界
（:data:`karte.verb_boundary._REFUSALS`）に含まれない。レポート本文（ファイル・標準入力）、
台帳、進行ポインタ、``--diff-file`` のどれを読む経路でも漏らさない。
"""

import argparse
import contextlib
import io
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from karte import cli, exit_codes, model, paths, utf8_text
from karte.errors import KarteUsageError

BAD = b"\xff\xfe"
REPO = Path(__file__).resolve().parent.parent.parent


class _RootedCase(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="karte-u8-")).resolve()
        self.addCleanup(lambda: shutil.rmtree(self.root, ignore_errors=True))
        (self.root / "tmp").mkdir()

    def _call(self, func, stdin=None, **kwargs):
        args = argparse.Namespace(repo_root=str(self.root), **kwargs)
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            if stdin is None:
                code = func(args)
            else:
                with mock.patch.object(sys, "stdin", stdin):
                    code = func(args)
        return code, err.getvalue()

    def _karte_dir(self):
        return paths.karte_dir(self.root, create=True)


class TestInvalidReportBody(_RootedCase):
    def test_invalid_utf8_report_file_is_exit_error_and_creates_nothing(self):
        (self.root / "bad.md").write_bytes(BAD)
        code, err = self._call(cli.cmd_ingest_review, issue="7", round="1", source="bad.md")
        self.assertEqual(exit_codes.EXIT_ERROR, code, err)
        self.assertIn("UTF-8", err)
        self.assertFalse((self.root / "tmp" / "_karte").exists())

    def test_invalid_utf8_stdin_is_exit_error_and_creates_nothing(self):
        stdin = io.TextIOWrapper(io.BytesIO(BAD), encoding="utf-8")
        code, err = self._call(cli.cmd_ingest_review, stdin, issue="7", round="1", source="-")
        self.assertEqual(exit_codes.EXIT_ERROR, code, err)
        self.assertIn("UTF-8", err)
        self.assertFalse((self.root / "tmp" / "_karte").exists())

    def test_surrogateescaped_stdin_is_exit_error_not_a_late_write_failure(self):
        """C ロケールの stdin は不正バイトを lone surrogate として通す。台帳へ書く前に拒否する。"""
        stdin = io.TextIOWrapper(
            io.BytesIO(b"### new\n" + BAD), encoding="utf-8", errors="surrogateescape"
        )
        code, err = self._call(cli.cmd_ingest_review, stdin, issue="7", round="1", source="-")
        self.assertEqual(exit_codes.EXIT_ERROR, code, err)
        self.assertFalse((self.root / "tmp" / "_karte").exists())

    def test_utf8_text_returns_valid_text_unchanged(self):
        self.assertEqual("日本語\n", utf8_text.read_stream_text(io.StringIO("日本語\n")))

    def test_utf8_text_rejects_undecodable_input_as_a_usage_error(self):
        with self.assertRaises(KarteUsageError):
            utf8_text.read_stream_text(io.TextIOWrapper(io.BytesIO(BAD), encoding="utf-8"))


class TestUnencodableWrites(_RootedCase):
    """argv に混じる lone surrogate は書込みで ``UnicodeEncodeError`` になる前に拒否し、何も書かない。"""

    def test_append_and_atomic_write_refuse_before_touching_the_file(self):
        target = self.root / "tmp" / "ledger.md"
        target.write_text("keep\n", encoding="utf-8")
        with self.assertRaises(KarteUsageError):
            paths.append_text(target, "x\udcff")
        with self.assertRaises(KarteUsageError):
            paths.write_text_atomic(target, "x\udcff")
        self.assertEqual("keep\n", target.read_text(encoding="utf-8"))
        self.assertFalse((self.root / "tmp" / "ledger.md.tmp").exists())

    def test_require_utf8_encodable_accepts_ordinary_text(self):
        utf8_text.require_utf8_encodable("日本語 ok", "x")


class TestInvalidLedgerAndPointerAndDiff(_RootedCase):
    def test_invalid_utf8_ledger_is_exit_error(self):
        paths.karte_path(7, self.root, create_dir=True).write_bytes(BAD)
        code, err = self._call(cli.cmd_status, issue="7", json=False)
        self.assertEqual(exit_codes.EXIT_ERROR, code, err)
        self.assertIn("UTF-8", err)

    def test_invalid_utf8_pointer_is_exit_error(self):
        paths.active_path(self.root, create_dir=True).write_bytes(BAD)
        code, err = self._call(cli.cmd_status, issue=None, json=False)
        self.assertEqual(exit_codes.EXIT_ERROR, code, err)
        self.assertIn("UTF-8", err)

    def test_invalid_utf8_ledger_is_exit_error_on_the_ingest_path_too(self):
        paths.karte_path(7, self.root, create_dir=True).write_bytes(BAD)
        stdin = io.StringIO("### new\n")
        code, err = self._call(cli.cmd_ingest_review, stdin, issue="7", round="1", source="-")
        self.assertEqual(exit_codes.EXIT_ERROR, code, err)
        self.assertIn("UTF-8", err)

    def test_invalid_utf8_diff_file_is_exit_error(self):
        karte = model.new_karte(7)
        karte.attempts.append(
            model.Attempt(
                number=1, round=1, finding_ids=["F-7-01"], root_cause="x",
                change_kind="logic", targets=["a.py::f"], diagnosis="",
            )
        )
        paths.karte_path(7, self.root, create_dir=True).write_text(
            model.dumps(karte), encoding="utf-8"
        )
        (self.root / "bad.diff").write_bytes(BAD)
        code, err = self._call(
            cli.cmd_close_attempt, issue="7", attempt="1", outcome="fixed",
            diff_file="bad.diff", base="HEAD", finding_ids=None, note="",
        )
        self.assertEqual(exit_codes.EXIT_ERROR, code, err)
        self.assertIn("UTF-8", err)  # 別の理由（Attempt 不在等）で拒否されて空振りしていない


class TestRealProcessExitCode(unittest.TestCase):
    """実プロセスで、不正な標準入力が traceback（1）ではなく 4 になる（引数が明示なので何も作らない）。"""

    def _run(self, **env_overrides):
        env = {k: v for k, v in os.environ.items() if k not in ("PYTHONIOENCODING", "PYTHONUTF8")}
        env.update(env_overrides)
        return subprocess.run(
            [sys.executable, "-m", "karte", "ingest-review", "--issue", "7", "--round", "1",
             "--from", "-"],
            input=BAD, cwd=str(REPO), env=env, capture_output=True,
        )

    def test_invalid_stdin_exits_with_the_fail_close_code(self):
        for locale in ("C.UTF-8", "C"):
            with self.subTest(locale=locale):
                done = self._run(LC_ALL=locale)
                self.assertEqual(exit_codes.EXIT_ERROR, done.returncode, done.stderr)
                self.assertNotIn(b"Traceback", done.stderr)


if __name__ == "__main__":
    unittest.main()
