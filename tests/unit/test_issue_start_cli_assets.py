"""Issue-start CLI I/O/exit codes と Codex/Claude asset parity。"""

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
                "policy_version": "issue-start/1.0",
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
    def test_both_harnesses_register_common_hook_core(self):
        codex = json.loads((ROOT / ".codex" / "hooks.json").read_text(encoding="utf-8"))
        claude = json.loads((ROOT / ".claude" / "settings.json").read_text(encoding="utf-8"))
        codex_matchers = {item.get("matcher") for item in codex["hooks"]["PreToolUse"]}
        claude_matchers = {item.get("matcher") for item in claude["hooks"]["PreToolUse"]}
        codex_dispatch_matcher = next(
            matcher for matcher in codex_matchers
            if isinstance(matcher, str) and "spawn_agent" in matcher
        )
        for tool_name in ("spawn_agent", "Agent", "collaborationspawn_agent"):
            with self.subTest(tool_name=tool_name):
                self.assertIsNotNone(re.fullmatch(codex_dispatch_matcher, tool_name))
        for similar_name in (
            "collaboration.spawn_agent",
            "evilspawn_agent",
            "collaborationspawn_agent_extra",
            "collaborationspawn_agents",
        ):
            with self.subTest(similar_name=similar_name):
                self.assertIsNone(re.fullmatch(codex_dispatch_matcher, similar_name))
        # Claude Code 2.1.221 は matcher `Task` で runtime tool_name `Agent` も捕捉する。
        self.assertIn("Task", claude_matchers)
        for script in [
            ROOT / ".codex" / "hooks" / "issue-start-gate.sh",
            ROOT / ".claude" / "hooks" / "issue-start-gate.sh",
        ]:
            self.assertIn("python3 -m issue_start.hook", script.read_text(encoding="utf-8"))

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
        self.assertEqual(manifest["managed"][0]["agent_type"], "issue-implementer")
        self.assertEqual(
            set(transports["codex"]["tool_names"]),
            {"spawn_agent", "collaborationspawn_agent"},
        )
        self.assertEqual(
            transports["codex"]["task_name_pattern"], "^issue_([1-9][0-9]*)$"
        )
        self.assertEqual(transports["codex"]["availability"], "unavailable")
        self.assertEqual(
            transports["codex"]["missing_observations"],
            [
                "child_workspace",
                "effective_tool_workspace",
                "actual_agent_id",
                "spawn_success",
            ],
        )
        self.assertNotIn("Agent", transports["codex"]["tool_names"])
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
        # Codex の spawn_agent には isolation 概念が無いので要求を持ち込まない（transport 別）。
        self.assertEqual(transports["claude"]["required_isolation"], "worktree")
        self.assertNotIn("required_isolation", transports["codex"])
        self.assertTrue(manifest["unmanaged"])

    def test_isolation_only_section_declares_the_fixer_contract(self):
        """Issue #354 PR-4: `issue-fixer` は「分離だけを課す」区分として宣言される。"""
        manifest = json.loads(
            (ROOT / "issue_start" / "managed-entrypoints-v2.json").read_text(encoding="utf-8")
        )
        entries = manifest["isolation_only"]
        self.assertEqual(len(entries), 1)
        entry = entries[0]
        self.assertEqual(entry["entrypoint"], "issue-pipeline")
        self.assertEqual(entry["agent_type"], "issue-fixer")
        transports = entry["binding_transports"]
        # Claude は tool isolation で到達する。Codex は shape を正規識別するが、
        # runtime observation 不足を manifest が宣言し dispatch 前に fail-close する。
        self.assertEqual(set(transports), {"claude", "codex"})
        codex = transports["codex"]
        self.assertEqual(set(codex["tool_names"]), {"spawn_agent", "collaborationspawn_agent"})
        self.assertEqual(codex["agent_type_field"], "agent_type")
        self.assertEqual(set(codex["required_tool_input_fields"]), {"agent_type", "task_name"})
        self.assertEqual(
            set(codex["forbidden_tool_input_fields"]), {"subagent_type", "prompt", "isolation"}
        )
        self.assertEqual(
            codex["task_name_pattern"],
            "^issue_([1-9][0-9]*)_fix_r([1-9][0-9]*)$",
        )
        self.assertEqual(codex["availability"], "unavailable")
        self.assertEqual(
            codex["missing_observations"],
            [
                "child_workspace",
                "effective_tool_workspace",
                "actual_agent_id",
                "spawn_success",
            ],
        )
        self.assertIn("prepare-only", codex["binding_source"])
        claude = transports["claude"]
        self.assertEqual(set(claude["tool_names"]), {"Task", "Agent"})
        self.assertEqual(claude["agent_type_field"], "subagent_type")
        self.assertEqual(set(claude["required_tool_input_fields"]), {"subagent_type", "prompt"})
        self.assertEqual(
            set(claude["forbidden_tool_input_fields"]), {"agent_type", "message", "task_name"}
        )
        self.assertEqual(claude["binding_marker"], "ISSUE_FIX_BINDING_V1=")
        self.assertEqual(claude["required_isolation"], "worktree")

    def test_managed_and_isolation_only_agent_types_are_disjoint(self):
        manifest = json.loads(
            (ROOT / "issue_start" / "managed-entrypoints-v2.json").read_text(encoding="utf-8")
        )
        managed = {item["agent_type"] for item in manifest["managed"]}
        isolation_only = {item["agent_type"] for item in manifest["isolation_only"]}
        self.assertFalse(managed & isolation_only)

    def test_existing_pre_tool_use_trust_indices_are_preserved(self):
        hooks = json.loads((ROOT / ".codex" / "hooks.json").read_text(encoding="utf-8"))
        groups = hooks["hooks"]["PreToolUse"]
        commands = [group["hooks"][0]["command"] for group in groups]
        self.assertIn("pr-merge-gate.sh", commands[0])
        self.assertIn("agent-command-gate.sh", commands[1])
        self.assertIn("issue-start-gate.sh", commands[2])
        self.assertIn("codex-workspace-binding-gate.sh", commands[3])
        self.assertEqual(len(groups), 4)

    def test_new_binding_hook_trust_does_not_enable_the_transport(self):
        manifest = json.loads(
            (ROOT / "issue_start" / "managed-entrypoints-v2.json").read_text(encoding="utf-8")
        )
        codex_transports = [
            entry["binding_transports"]["codex"]
            for section in ("managed", "isolation_only")
            for entry in manifest[section]
        ]
        self.assertTrue(codex_transports)
        self.assertTrue(all(item["availability"] == "unavailable" for item in codex_transports))
        readme = (ROOT / ".codex" / "hooks" / "README.md").read_text(encoding="utf-8")
        self.assertIn("pre_tool_use:3:0", readme)
        self.assertIn("Trusting group 3 does not enable the transport", readme)


if __name__ == "__main__":
    unittest.main()
