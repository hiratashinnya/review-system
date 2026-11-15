"""Issue #812: the agent-facing command contract must match the actual Claude gate.

The Markdown table is deliberately parsed rather than copied into a second fixture.
Each example is submitted to the *real* PreToolUse hook without executing gh/git.
"""
import ast
import json
import os
import re
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CONTRACT = ROOT / ".claude/agents/gh-create-issue.md"
GATE = ROOT / ".claude/hooks/agent-command-gate.sh"


def section(text, name):
    start = f"<!-- gh-create-issue-gate-{name}:start -->"
    end = f"<!-- gh-create-issue-gate-{name}:end -->"
    if text.count(start) != 1 or text.count(end) != 1:
        raise AssertionError(f"gate contract must have one {name} section")
    return text.split(start, 1)[1].split(end, 1)[0]


def table_rows(text):
    rows = []
    for line in text.splitlines():
        if not line.startswith("| "):
            continue
        parts = [p.strip() for p in line.strip().strip("|").split("|")]
        if parts[0] not in {"subcommand", "判定", "---"} and not parts[0].startswith("---"):
            rows.append(parts)
    return rows


def embedded_gate_ast():
    shell = GATE.read_text(encoding="utf-8")
    script = shell.split("<<'PYEOF'\n", 1)[1].split("\nPYEOF", 1)[0]
    return ast.parse(script)


class GhCreateIssueGateContractTests(unittest.TestCase):
    def test_documented_allowlist_equals_gate_source(self):
        rows = table_rows(section(CONTRACT.read_text(encoding="utf-8"), "allowlist"))
        documented = {}
        for row in rows:
            self.assertEqual(len(row), 3, row)
            names = re.findall(r"`([^`]+)`", row[0])
            self.assertEqual(len(names), 1, row)
            words = names[0].split()
            self.assertEqual(words[0], "gh")
            key = tuple(words[1:])
            self.assertNotIn(key, documented)
            documented[key] = set(re.findall(r"`(--[a-z-]+|-[A-Za-z])`", row[1]))

        function = next(
            node for node in embedded_gate_ast().body
            if isinstance(node, ast.FunctionDef) and node.name == "gh_create_issue_violation"
        )
        assignments = {
            target.id: statement.value
            for statement in function.body if isinstance(statement, ast.Assign)
            for target in statement.targets if isinstance(target, ast.Name)
        }
        allowed = ast.literal_eval(assignments["allowed"])
        # Gate uses the dict's .get(key, set()) to select subcommand flags.
        flags = ast.literal_eval(assignments["flags"].func.value)
        self.assertEqual(set(documented), allowed, "document and gate subcommands diverged")
        for key in allowed - {("api",)}:
            with self.subTest(subcommand=key):
                self.assertEqual(documented[key], flags[key],
                                 "document and gate option allowlists diverged")
        self.assertEqual(documented[("api",)], set(),
                         "API flags must be described by the API-specific rules")

    def test_every_documented_example_passes_the_real_gate(self):
        rows = table_rows(section(CONTRACT.read_text(encoding="utf-8"), "cases"))
        commands = set()
        outcomes = {"allow": 0, "deny": 0}
        for row in rows:
            self.assertEqual(len(row), 3, row)
            verdict, value, _ = row
            self.assertIn(verdict, outcomes)
            self.assertTrue(value.startswith("`") and value.endswith("`"), row)
            command = value[1:-1]
            self.assertNotIn(command, commands, "duplicate gate example")
            commands.add(command)
            outcomes[verdict] += 1
            with self.subTest(expected=verdict, command=command):
                result = subprocess.run(
                    [str(GATE)],
                    input=json.dumps({"agent_type": "gh-create-issue",
                                      "tool_input": {"command": command}}),
                    text=True, capture_output=True, cwd=ROOT, check=True,
                    env={**os.environ, "AGENT_COMMAND_GATE_TRACE_LOG": "",
                         "GH_REPO": "", "GH_HOST": ""},
                )
                self.assertFalse(result.stderr.strip(), result.stderr)
                actual = "allow" if not result.stdout.strip() else "deny"
                if actual == "deny":
                    payload = json.loads(result.stdout)
                    self.assertEqual(
                        payload["hookSpecificOutput"]["permissionDecision"], "deny"
                    )
                self.assertEqual(actual, verdict, result.stdout)
        self.assertGreaterEqual(outcomes["allow"], 20)
        self.assertGreaterEqual(outcomes["deny"], 15)
        for command in (
            "git branch --show-current", "git remote -v",
            "git remote get-url origin", "git status --short",
            "git status --short --branch"
        ):
            self.assertIn(command, commands, "all five git shapes must be covered")


if __name__ == "__main__":
    unittest.main()
