import ast
import fnmatch
import json
from pathlib import Path
import shlex
import tomllib
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
    def test_claude_native_rules_cover_shell_and_mcp_for_every_role(self):
        settings = json.loads((ROOT / ".claude/settings.json").read_text(encoding="utf-8"))
        denies = settings["permissions"]["deny"]
        bash_patterns = [item[5:-1] for item in denies if item.startswith("Bash(")]
        commands = (
            "gh pr merge 123 --merge", "rtk gh pr merge 123",
            "rtk proxy gh pr merge 123", "git merge feature",
            "rtk git merge feature", "rtk proxy git merge feature",
            "git -C /tmp/repo merge feature",
            "rtk git -C /tmp/repo merge feature",
            "rtk proxy git -C /tmp/repo merge feature",
            "gh -R owner/repo pr merge 123 --merge",
            "gh --repo owner/repo pr merge 123 --merge",
            "rtk gh -R owner/repo pr merge 123 --merge",
            "rtk gh --repo owner/repo pr merge 123 --merge",
            "rtk proxy gh -R owner/repo pr merge 123 --merge",
            "rtk proxy gh --repo owner/repo pr merge 123 --merge",
            "gh api -X PUT repos/o/r/pulls/123/merge",
            "rtk proxy gh api -X PUT repos/o/r/pulls/123/merge",
            "gh api graphql -F query=@mutation.graphql",
            "rtk proxy gh api graphql -F query=@mutation.graphql",
        )
        for role in ROLES:
            for command in commands:
                with self.subTest(role=role, command=command):
                    self.assertTrue(any(fnmatch.fnmatchcase(command, p) for p in bash_patterns))
            for tool in (
                "mcp__codex_apps__github_merge_pull_request",
                "mcp__codex_apps__github_enable_auto_merge",
                "mcp__github__merge_pull_request",
                "mcp__github__enable_auto_merge",
                "mcp__github__enable_pull_request_auto_merge",
                "github_merge_pull_request",
                "github_enable_auto_merge",
            ):
                self.assertIn(tool, denies)

    def test_codex_native_forbidden_rules_cover_shell_and_api_variants(self):
        prefixes = codex_forbidden_prefixes()
        commands = (
            "gh pr merge 123 --merge", "rtk gh pr merge 123",
            "rtk proxy gh pr merge 123", "git merge feature",
            "rtk git merge feature", "rtk proxy git merge feature",
            "rtk proxy git -c alias.m=merge m feature",
            "git -C /tmp/repo merge feature",
            "rtk git -C /tmp/repo merge feature",
            "rtk proxy git -C /tmp/repo merge feature",
            "git -C /tmp/repo status --short",
            "gh -R owner/repo pr merge 123",
            "gh --repo owner/repo pr merge 123",
            "rtk gh -R owner/repo pr merge 123",
            "rtk gh --repo owner/repo pr merge 123",
            "rtk proxy gh -R owner/repo pr merge 123",
            "rtk proxy gh --repo owner/repo pr merge 123",
            "gh -R owner/repo pr view 123",
            "gh api -X PUT repos/o/r/pulls/123/merge",
            "gh api graphql -F query=@mutation.graphql",
            "rtk gh api graphql -F query=@mutation.graphql",
            "rtk proxy gh api graphql -F query=@mutation.graphql",
        )
        for role in ROLES:
            for command in commands:
                with self.subTest(role=role, command=command):
                    self.assertTrue(codex_denies(command, prefixes))

    def test_no_classifier_hook_registration_or_reviewer_merge_allowance_remains(self):
        claude = json.loads((ROOT / ".claude/settings.json").read_text(encoding="utf-8"))
        codex_hooks = json.loads((ROOT / ".codex/hooks.json").read_text(encoding="utf-8"))
        self.assertNotIn("pr-merge-gate.sh", json.dumps(claude))
        self.assertNotIn("pr-merge-gate.sh", json.dumps(codex_hooks))
        self.assertFalse((ROOT / "pr_merge_gate/classifier.py").exists())
        self.assertFalse((ROOT / "pr_merge_gate/hook.py").exists())
        for path in (".claude/hooks/agent-command-gate.sh", ".codex/hooks/agent-command-gate.sh"):
            self.assertNotIn('("pr", "merge")', (ROOT / path).read_text(encoding="utf-8"))
        reviewer = tomllib.loads((ROOT / ".codex/agents/pr-reviewer.toml").read_text(encoding="utf-8"))
        self.assertIn("merge は実行しない", reviewer["description"])


if __name__ == "__main__":
    unittest.main()
