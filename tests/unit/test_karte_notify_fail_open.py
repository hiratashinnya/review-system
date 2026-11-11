"""``karte_notify`` の fail-open 境界と並び順の特性化（PR #696 第5回 R5-07・T-F4）。

通知フックは助言専用で、読めない・壊れた・想定外の入力はすべて無出力 ``exit 0`` か「初回扱い」に倒す。
``except`` 群の各要素と ``isinstance`` 検査は、外すと traceback かオーナーへの誤通知になるので、
入力の種類ごとに固定する。
"""

import io
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from karte_notify import hook, notify


class _Completed:
    def __init__(self, returncode=0, stdout=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = ""


class _RaisingStdin:
    def __init__(self, error):
        self.error = error

    def read(self, *_args):
        raise self.error


def _finding(finding_id, status="open"):
    return {"id": finding_id, "status": status}


class TestSortKey(unittest.TestCase):
    """finding ID の並びは (issue, seq) の数値順。ID として読めないものは落とさず先頭へ寄せる。"""

    def test_well_formed_ids_sort_numerically_not_lexically(self):
        self.assertEqual((512, 2), notify._sort_key("F-512-02"))
        self.assertEqual(
            ["F-9-20", "F-9-100"], sorted(["F-9-100", "F-9-20"], key=notify._sort_key)
        )

    def test_unparseable_id_falls_back_without_raising_and_sorts_first(self):
        self.assertEqual((0, "legacy-1"), notify._sort_key("legacy-1"))
        self.assertEqual(
            ["legacy-1", "F-512-09", "F-512-10"],
            sorted(["F-512-10", "legacy-1", "F-512-09"], key=notify._sort_key),
        )

    def test_decide_lists_an_unparseable_id_first_instead_of_failing(self):
        current = {
            "issue": 512, "verdict": "harmful-open", "escalate": False,
            "findings": [_finding("F-512-10"), _finding("legacy-1"), _finding("F-512-09")],
        }
        message, _snapshot = notify.decide(current, previous=None)
        assert message is not None
        positions = [message.index(item) for item in ("legacy-1", "F-512-09", "F-512-10")]
        self.assertEqual(sorted(positions), positions)


class TestReadSnapshotFailsOpen(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.dir = Path(temporary.name)
        self.path = self.dir / "issue-1.json"

    def test_a_valid_snapshot_is_returned(self):
        self.path.write_text('{"findings": {}}', encoding="utf-8")
        self.assertEqual({"findings": {}}, notify.read_snapshot(self.path))

    def test_unreadable_content_is_treated_as_a_first_run(self):
        cases = {
            "broken json": b"{ not json",
            "empty": b"",
            "not utf-8": b"\xff\xfe",
            "list": b"[]",
            "number": b"5",
            "null": b"null",
            "string": b'"x"',
        }
        for name, content in cases.items():
            with self.subTest(case=name):
                self.path.write_bytes(content)
                self.assertIsNone(notify.read_snapshot(self.path))

    def test_an_os_error_while_reading_is_treated_as_a_first_run(self):
        self.path.write_text('{"findings": {}}', encoding="utf-8")
        with mock.patch.object(Path, "read_text", side_effect=OSError("denied")):
            self.assertIsNone(notify.read_snapshot(self.path))

    def test_a_symlink_is_not_followed_even_when_it_points_at_a_valid_snapshot(self):
        target = self.dir / "elsewhere.json"
        target.write_text('{"findings": {"F-1-01": "resolved"}}', encoding="utf-8")
        self.path.symlink_to(target)
        self.assertIsNone(notify.read_snapshot(self.path))

    def test_a_directory_is_not_a_snapshot(self):
        self.path.mkdir()
        self.assertIsNone(notify.read_snapshot(self.path))


class TestLoadPayloadFailsOpen(unittest.TestCase):
    def test_a_tool_payload_object_is_returned(self):
        self.assertEqual({"tool_name": "Bash"}, hook._load_payload(io.StringIO('{"tool_name": "Bash"}')))

    def test_unusable_input_is_none(self):
        for name, text in {"broken": "{", "empty": "", "list": "[]", "number": "5", "null": "null"}.items():
            with self.subTest(case=name):
                self.assertIsNone(hook._load_payload(io.StringIO(text)))

    def test_a_read_failure_is_none(self):
        for error in (OSError("closed"), UnicodeDecodeError("utf-8", b"\xff", 0, 1, "bad")):
            with self.subTest(error=type(error).__name__):
                self.assertIsNone(hook._load_payload(_RaisingStdin(error)))  # type: ignore[arg-type]

    def test_undecodable_stdin_bytes_are_none(self):
        stdin = io.TextIOWrapper(io.BytesIO(b"\xff\xfe"), encoding="utf-8")
        self.assertIsNone(hook._load_payload(stdin))


class _HookCase(unittest.TestCase):
    TOOL = {
        "tool_name": "Bash",
        "tool_input": {"command": "python3 -m karte ingest-review --issue 512 --round 1 --from -"},
    }

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        (self.root / "tmp" / "_karte").mkdir(parents=True)
        self.stdout, self.stderr = io.StringIO(), io.StringIO()

    def invoke(self, runner, stdin_text=None):
        stdin = io.StringIO(json.dumps(self.TOOL) if stdin_text is None else stdin_text)
        return hook.run(
            stdin=stdin, stdout=self.stdout, stderr=self.stderr,
            project_root=self.root, runner=runner,
        )

    def reasons(self):
        return [json.loads(line).get("reason") for line in self.stderr.getvalue().splitlines()]


class TestStatusOutputFailsOpen(_HookCase):
    def test_unusable_status_stdout_is_a_silent_skip(self):
        for name, stdout in {
            "not json": "not json", "empty": "", "none": None, "list": "[]", "number": "5",
        }.items():
            with self.subTest(case=name):
                self.stdout, self.stderr = io.StringIO(), io.StringIO()
                code = self.invoke(lambda argv, **kw: _Completed(0, stdout))
                self.assertEqual(0, code)
                self.assertEqual("", self.stdout.getvalue())
                self.assertEqual(["STATUS_UNAVAILABLE"], self.reasons())

    def test_a_failed_status_command_is_a_silent_skip_even_if_it_printed_a_valid_payload(self):
        """終了コードが 0 以外なら、標準出力が読める JSON でも通知しない（失敗した判定を届けない）。"""
        body = json.dumps(
            {"issue": 512, "verdict": "harmful-open", "escalate": False, "findings": [_finding("F-512-01")]}
        )
        for returncode in (1, 2, 4):
            with self.subTest(returncode=returncode):
                self.stdout, self.stderr = io.StringIO(), io.StringIO()
                self.assertEqual(0, self.invoke(lambda argv, **kw: _Completed(returncode, body)))
                self.assertEqual("", self.stdout.getvalue())
                self.assertEqual(["STATUS_UNAVAILABLE"], self.reasons())

    def test_a_runner_that_cannot_start_the_command_is_a_silent_skip(self):
        def boom(argv, **kwargs):
            raise OSError("no python")

        self.assertEqual(0, self.invoke(boom))
        self.assertEqual("", self.stdout.getvalue())
        self.assertEqual(["STATUS_UNAVAILABLE"], self.reasons())

    def test_a_status_command_that_times_out_is_a_silent_skip(self):
        """``STATUS_TIMEOUT_S`` 超過（``TimeoutExpired``）は OSError ではないが同じく fail-open（#728）。"""

        def hang(argv, **kwargs):
            raise subprocess.TimeoutExpired(argv, kwargs["timeout"])

        self.assertEqual(0, self.invoke(hang))
        self.assertEqual("", self.stdout.getvalue())
        self.assertEqual(["STATUS_UNAVAILABLE"], self.reasons())

    def test_a_status_without_an_integer_issue_is_a_silent_skip(self):
        for issue in (None, "512", 1.5):
            with self.subTest(issue=issue):
                self.stdout, self.stderr = io.StringIO(), io.StringIO()
                body = json.dumps({"issue": issue, "verdict": "clean", "escalate": False, "findings": []})
                self.assertEqual(0, self.invoke(lambda argv, **kw: _Completed(0, body)))
                self.assertEqual("", self.stdout.getvalue())
                self.assertEqual(["ISSUE_UNRESOLVED"], self.reasons())


class TestSnapshotPathFailsOpen(_HookCase):
    def test_a_symlinked_snapshot_is_skipped_without_following_it(self):
        directory = self.root / "tmp" / "_karte" / "notified"
        directory.mkdir()
        target = self.root / "elsewhere.json"
        target.write_text("{}", encoding="utf-8")
        (directory / "issue-512.json").symlink_to(target)
        body = json.dumps({"issue": 512, "verdict": "clean", "escalate": False, "findings": []})
        self.assertEqual(0, self.invoke(lambda argv, **kw: _Completed(0, body)))
        self.assertEqual("", self.stdout.getvalue())
        self.assertEqual(["SNAPSHOT_PATH_ERROR"], self.reasons())
        self.assertEqual("{}", target.read_text(encoding="utf-8"))  # 書き込みも辿っていない


class TestUnusablePayloadIsSilent(_HookCase):
    def test_garbage_stdin_is_a_silent_exit_zero(self):
        for text in ("", "{", "[]", "null", '{"tool_name": "Bash"}', '{"tool_name": "Bash", "tool_input": 5}'):
            with self.subTest(stdin=text):
                runs = []
                self.assertEqual(
                    0, self.invoke(lambda argv, **kw: runs.append(argv) or _Completed(0, "{}"), text)
                )
                self.assertEqual("", self.stdout.getvalue())
                self.assertEqual([], runs)


if __name__ == "__main__":
    unittest.main()
