"""agy-delegate の起動元束縛: 両 PF の hook が、cwd 系の省略を含め実効 cwd を信頼ルートへ固定する。"""

import json
import tempfile
import unittest
from pathlib import Path
from typing import TypedDict

from agent_command_gate.launch_origin import launch_origin_reason
from tests.unit.test_agent_command_gate import payload as claude_payload, run_gate as claude_gate
from tests.unit.test_codex_agent_command_gate import payload as codex_payload, run_gate as codex_gate

ROOT = Path(__file__).resolve().parents[2]
COMMAND = "python3 -m agy_delegate run --workspace /tmp/work --settings /tmp/settings --executable /tmp/agy --prompt text --print-timeout 120 --caller-state ready"
LAUNCH_ROOT_MESSAGE = "agy_delegate launch root"


class LaunchCase(TypedDict, total=False):
    cwd: object
    tool_input: dict[str, object]
    process_cwd: Path
    omit_cwd: bool


def launch_codex(*, cwd: object | None = None, tool_input: dict[str, object] | None = None,
                 process_cwd: Path = ROOT, omit_cwd: bool = True):
    body = codex_payload("agy-delegate", COMMAND, tool_name="exec_command")
    if not omit_cwd or cwd is not None:
        body["cwd"] = cwd
    body["tool_input"].update(tool_input or {})
    return codex_gate(body, cwd=process_cwd)


def launch_claude(*, cwd: object | None = None, tool_input: dict[str, object] | None = None,
                  process_cwd: Path = ROOT, omit_cwd: bool = True):
    body = claude_payload("agy-delegate", COMMAND)
    if not omit_cwd or cwd is not None:
        body["cwd"] = cwd
    body["tool_input"].update(tool_input or {})
    return claude_gate(body, cwd=process_cwd, env={"CLAUDE_PROJECT_DIR": str(ROOT)})


class LaunchOriginBothPlatformsTests(unittest.TestCase):
    """cwd 系が省略・null でも、実プロセスの cwd が信頼ルートでなければ拒否する（呼出元 cwd 前提を持たない）。"""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.other = Path(self.temp.name) / "other-tree"
        (self.other / "agy_delegate").mkdir(parents=True)
        (self.other / "agy_delegate" / "__main__.py").write_text("raise SystemExit(0)\n")
        self.link = Path(self.temp.name) / "root-link"
        self.link.symlink_to(ROOT, target_is_directory=True)
        self.launchers = (("codex", launch_codex), ("claude", launch_claude))

    def test_launch_from_trusted_root_is_allowed_for_every_declaration_form(self):
        cases: tuple[LaunchCase, ...] = (
            {}, {"omit_cwd": False}, {"cwd": str(ROOT)}, {"cwd": str(self.link)},
            {"tool_input": {"workdir": str(ROOT)}}, {"tool_input": {"workdir": None}},
            {"cwd": str(ROOT), "tool_input": {"workdir": "."}},
            {"tool_input": {"cwd": str(self.link)}}, {"process_cwd": self.link},
        )
        for name, launch in self.launchers:
            for case in cases:
                with self.subTest(platform=name, case=case):
                    self.assertIsNone(launch(
                        cwd=case.get("cwd"), tool_input=case.get("tool_input"),
                        process_cwd=case.get("process_cwd", ROOT),
                        omit_cwd=case.get("omit_cwd", True),
                    ))

    def test_omitted_or_null_cwd_is_denied_when_real_process_cwd_is_not_trusted_root(self):
        for name, launch in self.launchers:
            for process_cwd in (self.other, ROOT / "tests", ROOT / "agy_delegate"):
                for omit in (True, False):
                    with self.subTest(platform=name, process_cwd=str(process_cwd), omit_cwd=omit):
                        denial = launch(process_cwd=process_cwd, omit_cwd=omit)
                        self.assertIsNotNone(denial)
                        self.assertIn(LAUNCH_ROOT_MESSAGE, json.dumps(denial))

    def test_omitted_cwd_with_trusted_workdir_still_requires_trusted_process_cwd(self):
        for name, launch in self.launchers:
            with self.subTest(platform=name):
                denial = launch(process_cwd=self.other, tool_input={"workdir": str(ROOT)})
                self.assertIsNotNone(denial)
                self.assertIn(LAUNCH_ROOT_MESSAGE, json.dumps(denial))

    def test_explicit_relative_and_invalid_values_are_denied(self):
        other = str(self.other)
        cases: tuple[LaunchCase, ...] = (
            {"cwd": other}, {"cwd": "."}, {"cwd": "relative/dir"}, {"cwd": 123}, {"cwd": ""},
            {"cwd": ["x"]}, {"cwd": str(ROOT / "tests")},
            {"tool_input": {"workdir": other}}, {"tool_input": {"cwd": other}},
            {"tool_input": {"workdir": "tests"}}, {"tool_input": {"workdir": ""}},
            {"tool_input": {"workdir": 123}}, {"tool_input": {"workdir": ["x"]}},
            {"cwd": str(ROOT), "tool_input": {"workdir": other}},
            {"cwd": other, "tool_input": {"workdir": str(ROOT)}},
            {"cwd": str(self.other / ".." / "other-tree")},
        )
        for name, launch in self.launchers:
            for case in cases:
                with self.subTest(platform=name, case=case):
                    denial = launch(
                        cwd=case.get("cwd"), tool_input=case.get("tool_input"),
                        process_cwd=case.get("process_cwd", ROOT),
                        omit_cwd=case.get("omit_cwd", True),
                    )
                    self.assertIsNotNone(denial)
                    self.assertIn(LAUNCH_ROOT_MESSAGE, json.dumps(denial))

    def test_missing_trusted_package_is_denied(self):
        empty = Path(self.temp.name) / "no-wrapper"
        empty.mkdir()
        reason = launch_origin_reason({"cwd": str(empty)}, {"command": COMMAND}, str(empty))
        if reason is None:
            self.fail("expected rejection when the trusted package is missing")
        self.assertIn("trusted agy_delegate package", reason)

    def test_wrong_command_is_still_denied_before_origin_check(self):
        for command in ("agy -p text", "python3 -m agy_delegate other", "python3 -c pass"):
            self.assertIsNotNone(claude_gate(claude_payload("agy-delegate", command), cwd=ROOT,
                                             env={"CLAUDE_PROJECT_DIR": str(ROOT)}))


class LaunchOriginModuleTests(unittest.TestCase):
    """実プロセス cwd を確定できない場合は、許可側に倒さず拒否する。"""

    def test_undeterminable_process_cwd_is_denied(self):
        def broken():
            raise FileNotFoundError("cwd removed")
        reason = launch_origin_reason({}, {"command": COMMAND}, str(ROOT), process_cwd=broken)
        if reason is None:
            self.fail("expected rejection when process cwd cannot be determined")
        self.assertIsNotNone(reason)
        self.assertIn(LAUNCH_ROOT_MESSAGE, reason)
        self.assertIn("cannot be determined", reason)

    def test_tool_input_not_a_mapping_does_not_bypass_cwd_check(self):
        self.assertIsNone(launch_origin_reason({"cwd": str(ROOT)}, None, str(ROOT)))
        self.assertIsNotNone(launch_origin_reason({"cwd": str(ROOT / "tests")}, None, str(ROOT)))
        self.assertIsNotNone(launch_origin_reason({}, None, str(ROOT), process_cwd=lambda: str(ROOT / "tests")))

    def test_relative_declaration_resolves_against_session_cwd_not_hook_process(self):
        self.assertIsNone(launch_origin_reason({"cwd": str(ROOT)}, {"workdir": "."}, str(ROOT),
                                               process_cwd=lambda: str(ROOT / "tests")))
        self.assertIsNotNone(launch_origin_reason({"cwd": str(ROOT)}, {"workdir": "tests"}, str(ROOT)))


if __name__ == "__main__":
    unittest.main()
