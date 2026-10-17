"""Issue-start CLI I/O/exit codes and Claude dispatch registration."""

import io
import json
from pathlib import Path
import re
import unittest
from unittest.mock import patch

from issue_start.cli import run


ROOT = Path(__file__).resolve().parents[2]
OID = "a" * 40
ARGS = [
    "--entrypoint", "issue-pipeline", "--repository", "example/repo",
    "--issue", "10",
]


class CliContractTests(unittest.TestCase):
    def test_allow_block_error_exit_codes_and_json_stdout(self):
        for verdict, code, reason in [
            ("ALLOW", 0, "ISSUE_START_ALLOWED"),
            ("BLOCK", 10, "OPEN_BLOCKER"),
            ("ERROR", 20, "API_UNAVAILABLE"),
        ]:
            evidence = {
                "schema_version": "issue-start-evidence/1",
                "policy_version": "issue-start/2.0",
                "result": verdict,
                "exit_code": code,
                "reason": reason,
            }
            stdout, stderr = io.StringIO(), io.StringIO()
            with patch("issue_start.cli.resolve_github_token", return_value=None), patch(
                "issue_start.cli.evaluate_issue_start", return_value=evidence
            ) as evaluate:
                actual = run(ARGS, stdout=stdout, stderr=stderr, cwd=ROOT)
            self.assertEqual(actual, code)
            self.assertEqual(json.loads(stdout.getvalue())["result"], verdict)
            self.assertIn(reason, stderr.getvalue())
            self.assertIsNone(evaluate.call_args.kwargs["token"])


class AssetParityTests(unittest.TestCase):
    def test_only_claude_registers_issue_start_hook(self):
        codex = json.loads((ROOT / ".codex" / "hooks.json").read_text(encoding="utf-8"))
        claude = json.loads((ROOT / ".claude" / "settings.json").read_text(encoding="utf-8"))
        codex_matchers = {item.get("matcher") for item in codex["hooks"]["PreToolUse"]}
        claude_matchers = {item.get("matcher") for item in claude["hooks"]["PreToolUse"]}
        self.assertFalse(any("spawn_agent" in str(matcher) for matcher in codex_matchers))
        self.assertIn("Task|Agent", claude_matchers)
        # Task / Agent の両方を正規 matcher で捕捉する。
        claude_hook = ROOT / ".claude" / "hooks" / "issue-start-gate.sh"
        self.assertIn("python3 -m issue_start.hook", claude_hook.read_text(encoding="utf-8"))

    def test_gate_reads_only_the_v2_manifest(self):
        """Issue #354 PR-4: 正本は v2 で、v1 は退役して**読まれない**。

        v1 ファイルは archive/issue-start-manifest-v1/ へ git mv 済み（PR8 区分1・
        archive/docidx-v1・archive/backref-v1 と同じ退役の見え方）。読み先が v2 だけで
        あることと v1 が退役を自己申告していることを機械的に固定する。
        """
        from issue_start.gate import ENTRYPOINT_MANIFEST, MANIFEST_SCHEMA_VERSION

        self.assertEqual(ENTRYPOINT_MANIFEST.name, "managed-entrypoints-v2.json")
        self.assertEqual(MANIFEST_SCHEMA_VERSION, "managed-issue-entrypoints/2")
        retired = json.loads(
            (ROOT / "archive" / "issue-start-manifest-v1" / "managed-entrypoints-v1.json")
            .read_text(encoding="utf-8")
        )
        self.assertEqual(retired["schema_version"], "managed-issue-entrypoints/1")
        self.assertIn("managed-entrypoints-v2.json", retired["retired"])

    def test_manifest_names_managed_and_unmanaged_paths(self):
        manifest = json.loads(
            (ROOT / "issue_start" / "managed-entrypoints-v2.json").read_text(encoding="utf-8")
        )
        self.assertEqual(manifest["schema_version"], "managed-issue-entrypoints/2")
        self.assertEqual(manifest["managed"][0]["entrypoint"], "issue-pipeline")
        transports = manifest["managed"][0]["binding_transports"]
        self.assertEqual(manifest["managed"][0]["agent_type"], "ac-designer")
        self.assertNotIn("codex", transports)
        self.assertEqual(set(transports["claude"]["tool_names"]), {"Task", "Agent"})
        self.assertEqual(
            set(transports["claude"]["required_tool_input_fields"]),
            {"subagent_type", "prompt"},
        )
        self.assertEqual(
            set(transports["claude"]["forbidden_tool_input_fields"]),
            {"agent_type", "message", "task_name"},
        )
        self.assertEqual(transports["claude"]["binding_marker"], "ISSUE_START_BINDING_V1=")
        # Issue #350: worktree 分離は Claude harness の Agent tool `isolation` で与えられる。
        # Claude の managed dispatch は Agent tool の isolation で worktree に分離する。
        self.assertEqual(transports["claude"]["required_isolation"], "worktree")
        self.assertTrue(manifest["unmanaged"])

    def test_isolation_only_section_declares_the_fixer_contract(self):
        """Issue #354 PR-4: `issue-fixer` は「分離だけを課す」区分として宣言される。"""
        manifest = json.loads(
            (ROOT / "issue_start" / "managed-entrypoints-v2.json").read_text(encoding="utf-8")
        )
        entries = manifest["isolation_only"]
        entry = next(item for item in entries if item["agent_type"] == "issue-fixer")
        self.assertEqual(entry["entrypoint"], "issue-pipeline")
        self.assertEqual(entry["agent_type"], "issue-fixer")
        transports = entry["binding_transports"]
        self.assertEqual(set(transports), {"claude"})
        claude = transports["claude"]
        self.assertEqual(set(claude["tool_names"]), {"Task", "Agent"})
        self.assertEqual(claude["agent_type_field"], "subagent_type")
        self.assertEqual(set(claude["required_tool_input_fields"]), {"subagent_type", "prompt"})
        self.assertEqual(
            set(claude["forbidden_tool_input_fields"]), {"agent_type", "message", "task_name"}
        )
        self.assertEqual(claude["binding_marker"], "ISSUE_FIX_BINDING_V1=")
        self.assertEqual(claude["required_isolation"], "worktree")

    def test_phase_roles_require_binding_and_observable_handover_before_launch(self):
        manifest = json.loads(
            (ROOT / "issue_start" / "managed-entrypoints-v2.json").read_text(encoding="utf-8")
        )
        writers = {"change-planner", "test-writer", "issue-implementer"}
        readers = {"issue-investigator", "plan-reviewer", "pr-reviewer", "adviser"}
        self.assertEqual(
            {entry["agent_type"] for entry in manifest["isolation_only"]},
            writers | {"issue-fixer"},
        )
        self.assertEqual({entry["agent_type"] for entry in manifest["readonly"]}, readers)
        for section in ("managed", "isolation_only", "readonly"):
            for entry in manifest[section]:
                role = entry["agent_type"]
                if role == "issue-fixer":
                    continue
                with self.subTest(role=role):
                    transport = entry["binding_transports"]["claude"]
                    self.assertEqual(transport["phase_binding_marker"], "ISSUE_PHASE_INPUT_V1=")
                    self.assertEqual(transport["availability"], "available")
                    missing = {"role-native-execution-evidence"}
                    if section == "readonly":
                        self.assertNotIn("required_isolation", transport)
                        self.assertNotIn("binding_marker", transport)
                    else:
                        expected = "ISSUE_START_BINDING_V1=" if role == "ac-designer" else "ISSUE_PHASE_BINDING_V1="
                        self.assertEqual(transport["binding_marker"], expected)
                        self.assertEqual(transport["required_isolation"], "worktree")
                        missing.add("worktree-handover-owner-decision")
                    self.assertNotIn("missing_observations", transport)

    def test_managed_isolation_only_and_readonly_agent_types_are_disjoint(self):
        manifest = json.loads(
            (ROOT / "issue_start" / "managed-entrypoints-v2.json").read_text(encoding="utf-8")
        )
        managed = {item["agent_type"] for item in manifest["managed"]}
        isolation_only = {item["agent_type"] for item in manifest["isolation_only"]}
        readonly = {item["agent_type"] for item in manifest["readonly"]}
        self.assertFalse(managed & isolation_only)
        self.assertFalse(managed & readonly)
        self.assertFalse(isolation_only & readonly)

    def test_retired_issue_start_registration_preserves_remaining_hooks(self):
        hooks = json.loads((ROOT / ".codex" / "hooks.json").read_text(encoding="utf-8"))
        groups = hooks["hooks"]["PreToolUse"]
        commands = [group["hooks"][0]["command"] for group in groups]
        self.assertEqual(len(groups), 1)
        self.assertIn("agent-command-gate.sh", commands[0])
        post_tool_commands = [
            group["hooks"][0]["command"] for group in hooks["hooks"]["PostToolUse"]
        ]
        self.assertEqual(len(post_tool_commands), 1)
        self.assertIn("adr-notify.sh", post_tool_commands[0])

    def test_manifest_keeps_only_the_claude_dispatch_sections(self):
        """Issue #538: Codex 起動用の top-level block は manifest から退役した。"""
        manifest = json.loads(
            (ROOT / "issue_start" / "managed-entrypoints-v2.json").read_text(encoding="utf-8")
        )
        self.assertEqual(
            set(manifest),
            {"schema_version", "policy_version", "managed", "isolation_only", "readonly", "unmanaged"},
        )

    def test_codex_hooks_register_only_scripts_that_exist(self):
        """Issue #538: 退役した launch gate を登録に残すと Codex の全 Bash 呼び出しが落ちる。"""
        hooks = json.loads((ROOT / ".codex" / "hooks.json").read_text(encoding="utf-8"))
        commands = [
            handler["command"]
            for groups in hooks["hooks"].values()
            for group in groups
            for handler in group["hooks"]
        ]
        self.assertTrue(commands)
        for command in commands:
            with self.subTest(command=command):
                self.assertNotIn("launch-intent", command)
                scripts = re.findall(
                    r'^bash "\$\(git rev-parse --show-toplevel\)/(\.codex/hooks/[a-z-]+\.sh)"$',
                    command,
                )
                self.assertEqual(len(scripts), 1)
                self.assertTrue((ROOT / scripts[0]).is_file())

    def test_retired_binding_hook_and_manifest_transport_are_absent(self):
        manifest = json.loads(
            (ROOT / "issue_start" / "managed-entrypoints-v2.json").read_text(encoding="utf-8")
        )
        codex_transports = [
            entry["binding_transports"].get("codex")
            for section in ("managed", "isolation_only", "readonly")
            for entry in manifest[section]
        ]
        self.assertTrue(all(item is None for item in codex_transports))
        readme = (ROOT / ".codex" / "hooks" / "README.md").read_text(encoding="utf-8")
        self.assertNotIn("pre_tool_use:3:0", readme)
        self.assertFalse((ROOT / ".codex" / "hooks" / "codex-workspace-binding-gate.sh").exists())


if __name__ == "__main__":
    unittest.main()
