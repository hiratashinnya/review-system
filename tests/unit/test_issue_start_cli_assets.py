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
        # Codex の spawn_agent には isolation 概念が無いので要求を持ち込まない（transport 別）。
        self.assertEqual(transports["claude"]["required_isolation"], "worktree")
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
        self.assertIn("codex-launch-intent-gate.sh", commands[3])
        self.assertEqual(groups[3]["matcher"], "Bash")
        self.assertEqual(len(groups), 4)

    def test_codex_launch_manifest_derives_every_non_owner_input(self):
        manifest = json.loads(
            (ROOT / "issue_start" / "managed-entrypoints-v2.json").read_text(encoding="utf-8")
        )
        launch = manifest["codex_supervisor_launch"]
        self.assertEqual(launch["schema_version"], "codex-launch-intent/1")
        self.assertEqual(launch["change_plan_schema"], "codex-change-plan/2")
        self.assertEqual(launch["change_plan_root"], "tmp/_codex_control/change-plans")
        self.assertEqual(launch["canonical_ledger_platform"], "codex-supervisor")
        self.assertEqual(launch["reservation_contract"], "same-entry/intent-digest-v1")
        self.assertEqual(launch["issuer_contract"], {
            "schema_version": "codex-change-plan-issuance/1",
            "command": "python3 -m issue_start.codex_launch_control issue",
            "sources_root": "tmp/_codex_control/sources",
        })
        self.assertEqual(set(launch["roles"]), {"issue-implementer", "issue-fixer"})
        self.assertEqual(launch["executables"], {
            "bwrap": "/usr/bin/bwrap",
            "codex": {"lookup_name": "codex",
                      "sandbox_alias": "/run/issue-supervised/codex"},
        })
        self.assertEqual(launch["permission_profile"], "issue-supervised")
        for role, config in launch["roles"].items():
            with self.subTest(role=role):
                self.assertEqual(
                    set(config),
                    {"model", "reasoning_effort", "task_key_template", "handoff_template",
                     "prompt_template"},
                )
                self.assertTrue(all(isinstance(value, str) and value for value in config.values()))
                self.assertIn("{issue_snapshot}", config["prompt_template"])
        self.assertIn("{karte_snapshot}", launch["roles"]["issue-fixer"]["prompt_template"])

    def test_codex_launch_hook_asset_is_registered_and_executable(self):
        script = ROOT / ".codex/hooks/codex-launch-intent-gate.sh"
        self.assertTrue(script.is_file())
        self.assertTrue(script.stat().st_mode & 0o111)
        self.assertIn("python3 -m issue_start.codex_launch_intent hook",
                      script.read_text(encoding="utf-8"))
        self.assertIn("--git-common-dir", script.read_text(encoding="utf-8"))
        self.assertIn('cd "$PROJECT_ROOT"', script.read_text(encoding="utf-8"))

    def test_retired_binding_hook_and_manifest_transport_are_absent(self):
        manifest = json.loads(
            (ROOT / "issue_start" / "managed-entrypoints-v2.json").read_text(encoding="utf-8")
        )
        codex_transports = [
            entry["binding_transports"].get("codex")
            for section in ("managed", "isolation_only")
            for entry in manifest[section]
        ]
        self.assertTrue(all(item is None for item in codex_transports))
        readme = (ROOT / ".codex" / "hooks" / "README.md").read_text(encoding="utf-8")
        self.assertNotIn("pre_tool_use:3:0", readme)
        self.assertFalse((ROOT / ".codex" / "hooks" / "codex-workspace-binding-gate.sh").exists())


if __name__ == "__main__":
    unittest.main()
