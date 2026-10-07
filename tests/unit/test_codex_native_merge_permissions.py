import ast
import fnmatch
import json
from pathlib import Path
import shlex
import unittest


ROOT = Path(__file__).resolve().parents[2]
ROLES = ("main", "pr-reviewer", "issue-implementer", "issue-fixer")


def codex_forbidden_prefixes():
    source = (ROOT / ".codex/rules/default.rules").read_text(encoding="utf-8")
    tree = ast.parse(source)
    prefixes = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or getattr(node.func, "id", None) != "prefix_rule":
            continue
        values = {item.arg: ast.literal_eval(item.value) for item in node.keywords}
        if values.get("decision") == "forbidden":
            prefixes.add(tuple(values["pattern"]))
    return prefixes


def codex_denies(command, prefixes):
    tokens = shlex.split(command)
    return any(tokens[:len(prefix)] == list(prefix) for prefix in prefixes)


class NativeMergePermissionTests(unittest.TestCase):
    def test_codex_native_forbidden_rules_cover_shell_and_api_variants(self):
        prefixes = codex_forbidden_prefixes()
        commands = (
            "gh pr merge 123 --merge", "rtk gh pr merge 123",
            "rtk proxy gh pr merge 123", "git merge feature",
            "rtk git merge feature", "rtk proxy git merge feature",
        )
        for role in ROLES:
            for command in commands:
                with self.subTest(role=role, command=command):
                    self.assertTrue(codex_denies(command, prefixes))

    def test_native_rules_allow_read_only_repository_and_api_calls(self):
        settings = json.loads((ROOT / ".claude/settings.json").read_text(encoding="utf-8"))
        denies = settings["permissions"]["deny"]
        bash_patterns = [item[5:-1] for item in denies if item.startswith("Bash(")]
        reads = (
            "git -C /tmp/repo status --short",
            "gh pr view 123",
            "gh --repo owner/repo pr view 123",
            "gh api --method GET repos/o/r/issues/123",
            "gh api graphql -F 'query={ viewer { login } }'",
        )
        for command in reads:
            with self.subTest(platform="claude", command=command):
                self.assertFalse(any(fnmatch.fnmatchcase(command, pattern) for pattern in bash_patterns))

        prefixes = codex_forbidden_prefixes()
        for command in reads:
            with self.subTest(platform="codex", command=command):
                self.assertFalse(codex_denies(command, prefixes))


if __name__ == "__main__":
    unittest.main()
