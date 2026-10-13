"""実際の PF hook に wrapper 起動を渡し、外側ゲートの範囲を検査する。"""

import json
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


if __name__ == "__main__":
    unittest.main()
