"""Issue #812: the documented gh-create-issue allowlist is an executable contract."""
import ast
import re
import unittest

from tests.unit.gh_create_issue_gate_contract_support import (
    CONTRACT, embedded_gate_ast, gate_decision, section, table_rows,
)


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
                self.assertEqual(gate_decision(command), verdict)
        self.assertGreaterEqual(outcomes["allow"], 22)
        self.assertGreaterEqual(outcomes["deny"], 19)
        for command in (
            "git branch --show-current", "git remote -v",
            "git remote get-url origin", "git status --short",
            "git status --short --branch",
        ):
            self.assertIn(command, commands, "all five git shapes must be covered")


if __name__ == "__main__":
    unittest.main()
