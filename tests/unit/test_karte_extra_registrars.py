"""``build_parser`` / ``main`` の ``extra_registrars``：別モジュールの verb を足せること。

登録 verb は ``fail_close(locked=...)`` でロック要否を宣言しなければならず、宣言の無い verb は
``build_parser`` が拒否する（PR #696 レビュー L-2）。
"""

import contextlib
import fcntl
import io
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from karte import cli, paths, verb_support
from karte.errors import KarteNotFound, KarteUsageError
from karte.exit_codes import EXIT_ERROR, EXIT_NOT_FOUND
from karte.model import KarteFormatError
from karte.path_errors import KartePathError
from karte.verb_boundary import fail_close


def _registrar_for(name, func):
    def register(subparsers, add_issue):
        verb = subparsers.add_parser(name, help="テスト用の verb")
        add_issue(verb)
        verb.set_defaults(func=func)

    return register


_register_probe = _registrar_for("probe", fail_close(locked=False)(lambda args, root: 42))


def _writer_lock_is_held(repo_root) -> bool:
    """別の file description から非ブロッキングで取りに行き、取れなければ誰かが握っている。"""
    lock_path = paths.karte_dir(repo_root, create=True) / ".writer.lock"
    with open(lock_path, "a+") as handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return True
        fcntl.flock(handle, fcntl.LOCK_UN)
        return False


class _RootedCase(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="karte-reg-")).resolve()
        self.addCleanup(lambda: shutil.rmtree(self.root, ignore_errors=True))
        (self.root / "tmp").mkdir()
        patcher = mock.patch.object(verb_support, "_REPO_ROOT", self.root)
        patcher.start()
        self.addCleanup(patcher.stop)


class TestExtraRegistrars(_RootedCase):
    def test_registered_verb_appears_in_the_parser(self):
        parser = cli.build_parser((_register_probe,))
        args = parser.parse_args(["probe", "--issue", "7"])
        self.assertEqual("7", args.issue)
        self.assertEqual(42, args.func(args))

    def test_main_dispatches_to_a_registered_verb(self):
        self.assertEqual(42, cli.main(["probe"], extra_registrars=(_register_probe,)))

    def test_verb_is_absent_without_the_registrar(self):
        with self.assertRaises(SystemExit):
            cli.build_parser().parse_args(["probe"])

    def test_existing_verbs_are_unchanged_by_registrars(self):
        verbs = {"ingest-review", "render", "append", "close-attempt", "check", "status"}
        parser = cli.build_parser((_register_probe,))
        for verb in verbs:
            with self.subTest(verb=verb):
                self.assertTrue(parser.parse_args([verb, "--issue", "1"] + (
                    ["--from", "x"] if verb == "ingest-review" else []
                ) + (
                    ["--finding-ids", "F-1-01", "--root-cause", "x", "--change-kind", "logic",
                     "--targets", "a.py::f"] if verb == "append" else []
                ) + (["--outcome", "fixed"] if verb == "close-attempt" else [])).func)

    def test_every_builtin_verb_declares_its_lock_requirement(self):
        locked = {"ingest-review": True, "append": True, "close-attempt": True,
                  "render": False, "check": False, "status": False}
        subparsers = next(
            action for action in cli.build_parser()._actions if action.dest == "verb"
        )
        for verb, expected in locked.items():
            with self.subTest(verb=verb):
                self.assertIs(expected, subparsers.choices[verb].get_default("func").locked)


class TestUndeclaredVerbIsRejected(unittest.TestCase):
    """ロック要否を宣言しない登録 verb は、組み立ての時点で拒否する（静かにロックなしで動かさない）。"""

    def test_plain_function_registration_is_rejected_by_build_parser(self):
        register = _registrar_for("bare", lambda args: 0)
        with self.assertRaises(ValueError) as caught:
            cli.build_parser((register,))
        self.assertIn("bare", str(caught.exception))

    def test_main_rejects_it_before_running_anything(self):
        calls = []
        register = _registrar_for("bare", lambda args: calls.append(args) or 0)
        with self.assertRaises(ValueError):
            cli.main(["bare"], extra_registrars=(register,))
        self.assertEqual([], calls)

    def test_locked_must_be_given_explicitly_as_a_bool(self):
        with self.assertRaises(TypeError):
            fail_close()
        with self.assertRaises(TypeError):
            fail_close(locked=None)
        with self.assertRaises(TypeError):
            fail_close(locked=1)


class TestDeclaredLockIsApplied(_RootedCase):
    """宣言どおりに適用される：locked=True の verb は writer lock の内側で、False はロックなしで走る。"""

    def _lock_is_held_during(self, locked):
        observed = []

        def verb(args, repo_root):
            observed.append(_writer_lock_is_held(repo_root))
            return 0

        register = _registrar_for("probe", fail_close(locked=locked)(verb))
        self.assertEqual(0, cli.main(["probe"], extra_registrars=(register,)))
        return observed[0]

    def test_locked_true_runs_inside_the_writer_lock(self):
        self.assertTrue(self._lock_is_held_during(True))

    def test_locked_false_runs_without_the_writer_lock(self):
        self.assertFalse(self._lock_is_held_during(False))

    def test_prepare_runs_before_the_lock_and_hands_its_result_to_the_verb(self):
        observed = []

        def prepare(args, repo_root):
            observed.append(("prepare", _writer_lock_is_held(repo_root)))
            return "prepared-value"

        def verb(args, repo_root, prepared):
            observed.append(("verb", _writer_lock_is_held(repo_root), prepared))
            return 0

        register = _registrar_for("probe", fail_close(locked=True, prepare=prepare)(verb))
        self.assertEqual(0, cli.main(["probe"], extra_registrars=(register,)))
        self.assertEqual(
            [("prepare", False), ("verb", True, "prepared-value")], observed
        )

    def test_prepare_refusal_happens_before_the_lock_creates_anything(self):
        def prepare(args, repo_root):
            raise KarteUsageError("early")

        register = _registrar_for(
            "probe", fail_close(locked=True, prepare=prepare)(lambda a, r, p: 0)
        )
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(EXIT_ERROR, cli.main(["probe"], extra_registrars=(register,)))
        self.assertFalse((self.root / "tmp" / "_karte").exists())

    def test_repo_root_is_resolved_once_per_run(self):
        register = _registrar_for("probe", fail_close(locked=True)(lambda args, root: 0))
        with mock.patch("karte.verb_boundary.repo_root_of", return_value=self.root) as resolver:
            self.assertEqual(0, cli.main(["probe"], extra_registrars=(register,)))
        self.assertEqual(1, resolver.call_count)

    def test_verb_receives_the_resolved_repo_root(self):
        seen = []
        register = _registrar_for(
            "probe", fail_close(locked=False)(lambda args, root: seen.append(root) or 0)
        )
        cli.main(["probe"], extra_registrars=(register,))
        self.assertEqual([self.root], seen)


def _registrar_raising(exc):
    def _raise(args, repo_root):
        raise exc

    return _registrar_for("boom", fail_close(locked=False)(_raise))


class TestExtraVerbFailClose(_RootedCase):
    """``fail_close`` で包んだ登録 verb は、何を投げても終了コード契約の中に収まる。"""

    def _main(self, exc):
        with contextlib.redirect_stderr(io.StringIO()):
            return cli.main(["boom"], extra_registrars=(_registrar_raising(exc),))

    def test_refusal_errors_become_exit_error(self):
        for exc in (KarteUsageError("u"), KartePathError("p"), KarteFormatError("f"), OSError("o")):
            with self.subTest(exc=type(exc).__name__):
                self.assertEqual(EXIT_ERROR, self._main(exc))

    def test_not_found_becomes_exit_not_found(self):
        self.assertEqual(EXIT_NOT_FOUND, self._main(KarteNotFound("n")))

    def test_repo_root_resolution_failure_is_inside_the_boundary(self):
        register = _registrar_for("probe", fail_close(locked=False)(lambda args, root: 0))
        with mock.patch(
            "karte.verb_boundary.repo_root_of", side_effect=KartePathError("broken .git")
        ), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(EXIT_ERROR, cli.main(["probe"], extra_registrars=(register,)))


if __name__ == "__main__":
    unittest.main()
