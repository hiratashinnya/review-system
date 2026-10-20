"""実際の PF hook に wrapper 起動を渡し、外側ゲートの範囲を検査する。"""

import json
import tempfile
import unittest
from pathlib import Path

from tests.unit.test_agent_command_gate import payload as claude_payload, run_gate as claude_gate
from tests.unit.test_codex_agent_command_gate import payload as codex_payload, run_gate as codex_gate

ROOT = Path(__file__).resolve().parents[2]
COMMAND = "python3 -m agy_delegate run --workspace /tmp/work --settings /tmp/settings --executable /tmp/agy --prompt text --print-timeout 120 --caller-state ready"


class GateTests(unittest.TestCase):
    def test_claude_bash_has_registered_gate_and_accepts_delegate_outer_command(self):
        settings = json.loads((ROOT / ".claude/settings.json").read_text())
        entries = settings["hooks"]["PreToolUse"]
        self.assertTrue(any("Bash" in entry.get("matcher", "") and
                            any("agent-command-gate.sh" in hook.get("command", "")
                                for hook in entry.get("hooks", [])) for entry in entries))
        self.assertIsNone(claude_gate(claude_payload("agy-delegate", COMMAND)))

    def test_codex_uses_its_own_hook_outer_command_only(self):
        self.assertIsNone(codex_gate(codex_payload("agy-delegate", COMMAND, tool_name="exec_command")))
        for gate, payload in ((claude_gate, claude_payload), (codex_gate, codex_payload)):
            self.assertIsNotNone(gate(payload("issue-implementer", COMMAND)))
            self.assertIsNotNone(gate(payload("agy-delegate", COMMAND + "; git merge main")))
            for command in ("agy -p text", "python3 -c pass", "python3 -m agy_delegate other", "git status", "git diff"):
                self.assertIsNotNone(gate(payload("agy-delegate", command)))


class CodexLaunchOriginTests(unittest.TestCase):
    """`python3 -m agy_delegate` は cwd の package を実行するため、起動元を hook の repo ルートに束縛する。"""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.other = Path(self.temp.name) / "other-tree"
        (self.other / "agy_delegate").mkdir(parents=True)
        (self.other / "agy_delegate" / "__main__.py").write_text("raise SystemExit(0)\n")

    def gate(self, *, cwd=None, tool_input=None):
        body = codex_payload("agy-delegate", COMMAND, tool_name="exec_command")
        if cwd is not None:
            body["cwd"] = cwd
        body["tool_input"].update(tool_input or {})
        return codex_gate(body, cwd=ROOT)

    def test_launch_from_hook_repository_root_is_allowed(self):
        link = Path(self.temp.name) / "root-link"
        link.symlink_to(ROOT, target_is_directory=True)
        self.assertIsNone(self.gate())
        self.assertIsNone(self.gate(cwd=str(ROOT)))
        self.assertIsNone(self.gate(cwd=str(link)))
        self.assertIsNone(self.gate(tool_input={"workdir": str(ROOT)}))
        self.assertIsNone(self.gate(cwd=str(ROOT), tool_input={"workdir": "."}))

    def test_different_launch_origin_is_denied_even_with_valid_command(self):
        other = str(self.other)
        for case in (dict(cwd=other), dict(tool_input={"workdir": other}),
                     dict(tool_input={"cwd": other}), dict(cwd=str(ROOT), tool_input={"workdir": other}),
                     dict(cwd=other, tool_input={"workdir": str(ROOT)}),
                     dict(cwd=str(ROOT / "tests")), dict(tool_input={"workdir": "tests"}),
                     dict(tool_input={"workdir": ""}), dict(tool_input={"workdir": 123}),
                     dict(cwd=str(self.other / ".." / "other-tree"))):
            with self.subTest(case=case):
                denial = self.gate(**case)
                self.assertIsNotNone(denial)
                self.assertIn("agy_delegate launch root", json.dumps(denial))

    def test_missing_trusted_package_at_hook_root_is_denied(self):
        empty = Path(self.temp.name) / "no-wrapper"
        empty.mkdir()
        body = codex_payload("agy-delegate", COMMAND, tool_name="exec_command")
        denial = codex_gate(body, cwd=empty)
        self.assertIsNotNone(denial)
        self.assertIn("trusted agy_delegate package", json.dumps(denial))


if __name__ == "__main__":
    unittest.main()
