"""不正な UTF-8 の入力は、traceback（終了コード 1）ではなく fail-close（終了コード 4）に収める（F-696-13）。

``UnicodeDecodeError`` は ``ValueError`` 系で、文書化された終了コード {0,2,3,4} の境界
（:data:`karte.verb_boundary._REFUSALS`）に含まれない。レポート本文（ファイル・標準入力）、
台帳、進行ポインタ、``--diff-file`` のどれを読む経路でも漏らさない。
"""

import io
import os
import subprocess
import sys
import unittest

from karte import exit_codes, model, paths, utf8_text
from karte.errors import KarteUsageError
from tests.unit.karte_support import RootedCase, ingest_argv, karte_sandbox

BAD = b"\xff\xfe"


class _Utf8Case(RootedCase):
    prefix = "karte-u8-"


class TestInvalidReportBody(_Utf8Case):
    def test_invalid_utf8_report_file_is_exit_error_and_creates_nothing(self):
        (self.root / "bad.md").write_bytes(BAD)
        code, _out, err = self.run_verb(ingest_argv(7, 1, "bad.md"))
        self.assertEqual(exit_codes.EXIT_ERROR, code, err)
        self.assertIn("UTF-8", err)
        self.assertFalse((self.root / "tmp" / "_karte").exists())

    def test_invalid_utf8_stdin_is_exit_error_and_creates_nothing(self):
        stdin = io.TextIOWrapper(io.BytesIO(BAD), encoding="utf-8")
        code, _out, err = self.run_verb(ingest_argv(7, 1), stdin)
        self.assertEqual(exit_codes.EXIT_ERROR, code, err)
        self.assertIn("UTF-8", err)
        self.assertFalse((self.root / "tmp" / "_karte").exists())

    def test_surrogateescaped_stdin_is_exit_error_not_a_late_write_failure(self):
        """C ロケールの stdin は不正バイトを lone surrogate として通す。台帳へ書く前に拒否する。"""
        stdin = io.TextIOWrapper(
            io.BytesIO(b"### new\n" + BAD), encoding="utf-8", errors="surrogateescape"
        )
        code, _out, err = self.run_verb(ingest_argv(7, 1), stdin)
        self.assertEqual(exit_codes.EXIT_ERROR, code, err)
        self.assertFalse((self.root / "tmp" / "_karte").exists())

    def test_utf8_text_returns_valid_text_unchanged(self):
        self.assertEqual("日本語\n", utf8_text.read_stream_text(io.StringIO("日本語\n")))

    def test_utf8_text_rejects_undecodable_input_as_a_usage_error(self):
        with self.assertRaises(KarteUsageError):
            utf8_text.read_stream_text(io.TextIOWrapper(io.BytesIO(BAD), encoding="utf-8"))


class TestUnencodableWrites(_Utf8Case):
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


class TestInvalidLedgerAndPointerAndDiff(_Utf8Case):
    def test_invalid_utf8_ledger_is_exit_error(self):
        paths.karte_path(7, self.root, create_dir=True).write_bytes(BAD)
        code, _out, err = self.run_verb(["status", "--issue", "7"])
        self.assertEqual(exit_codes.EXIT_ERROR, code, err)
        self.assertIn("UTF-8", err)

    def test_invalid_utf8_pointer_is_exit_error(self):
        paths.active_path(self.root, create_dir=True).write_bytes(BAD)
        code, _out, err = self.run_verb(["status"])
        self.assertEqual(exit_codes.EXIT_ERROR, code, err)
        self.assertIn("UTF-8", err)

    def test_invalid_utf8_ledger_is_exit_error_on_the_ingest_path_too(self):
        paths.karte_path(7, self.root, create_dir=True).write_bytes(BAD)
        stdin = io.StringIO("### new\n")
        code, _out, err = self.run_verb(ingest_argv(7, 1), stdin)
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
        code, _out, err = self.run_verb(
            ["close-attempt", "--issue", "7", "--attempt", "1", "--outcome", "fixed",
             "--diff-file", "bad.diff"]
        )
        self.assertEqual(exit_codes.EXIT_ERROR, code, err)
        self.assertIn("UTF-8", err)  # 別の理由（Attempt 不在等）で拒否されて空振りしていない


class TestRealProcessExitCode(unittest.TestCase):
    """実プロセスで、不正な標準入力が traceback（1）ではなく 4 になる。

    パッケージを一時ディレクトリへ複製して走らせる（台帳の置き場はパッケージの親になるので、
    退行して拒否がロック内に戻っても実リポジトリ側 ``tmp/_karte/`` には何も作られない）。
    """

    def setUp(self):
        self.sandbox = karte_sandbox(self)

    def _run(self, **env_overrides):
        env = {k: v for k, v in os.environ.items() if k not in ("PYTHONIOENCODING", "PYTHONUTF8")}
        env.update(env_overrides)
        return subprocess.run(
            [sys.executable, "-m", "karte", "ingest-review", "--issue", "7", "--round", "1",
             "--from", "-"],
            input=BAD, cwd=str(self.sandbox), env=env, capture_output=True,
        )

    def test_invalid_stdin_exits_with_the_fail_close_code(self):
        for locale in ("C.UTF-8", "C"):
            with self.subTest(locale=locale):
                done = self._run(LC_ALL=locale)
                self.assertEqual(exit_codes.EXIT_ERROR, done.returncode, done.stderr)
                self.assertNotIn(b"Traceback", done.stderr)
                self.assertFalse((self.sandbox / "tmp").exists())  # 引数が明示なので何も作らない


if __name__ == "__main__":
    unittest.main()
