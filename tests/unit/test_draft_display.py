"""draft_display（gh-create-issue サブエージェント成果物の直送フック）の単体テスト。

SubagentStop で handoff 本文を ``systemMessage`` として表示する。可視化専用で、
判定不能な経路はすべて無出力・exit 0（fail-open）。PostToolUse は使わない
（非同期移譲では SubagentStart より前に発火し用途に合わないため）。
"""

import io
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from draft_display import handoff, stop

ROOT = Path(__file__).resolve().parents[2]
HOOK_DIR = ROOT / ".claude" / "hooks"
REL = "tmp/_handoff/gh-create-issue--20261013T000000Z.md"


class _Workspace(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        (self.root / "tmp" / "_handoff").mkdir(parents=True)

    def write_handoff(self, text="# draft\n本文", rel=REL):
        path = self.root / rel
        path.write_text(text, encoding="utf-8")
        return path

    def run_hook(self, module, payload):
        stdout, stderr = io.StringIO(), io.StringIO()
        code = module.run(
            stdin=io.StringIO(json.dumps(payload)), stdout=stdout, stderr=stderr,
            project_root=self.root,
        )
        return code, stdout.getvalue(), stderr.getvalue()


class FindAndResolveTests(_Workspace):
    def test_last_handoff_line_wins(self):
        text = f"HANDOFF: {REL}\nx\nHANDOFF: tmp/_handoff/gh-create-issue--b.md\n"
        self.assertEqual(handoff.find_handoff_rel(text), "tmp/_handoff/gh-create-issue--b.md")

    def test_rejects_paths_outside_the_contract(self):
        for bad in (
            "HANDOFF: tmp/_handoff/other-agent--a.md",
            "HANDOFF: tmp/_handoff/../secret.md",
            "HANDOFF: /etc/passwd",
            "HANDOFF: tmp/_handoff/sub/gh-create-issue--a.md",
            "HANDOFF: tmp/_handoff/gh-create-issue--a.yaml",
            "no handoff here",
        ):
            with self.subTest(bad=bad):
                self.assertIsNone(handoff.find_handoff_rel(bad))

    def test_resolve_accepts_regular_file_only(self):
        path = self.write_handoff()
        self.assertEqual(handoff.resolve_handoff(self.root, REL), path)
        self.assertIsNone(
            handoff.resolve_handoff(self.root, "tmp/_handoff/gh-create-issue--missing.md")
        )

    def test_resolve_rejects_symlink(self):
        target = self.root / "secret.md"
        target.write_text("secret", encoding="utf-8")
        link = self.root / REL
        try:
            link.symlink_to(target)
        except OSError:
            self.skipTest("symlink unsupported")
        self.assertIsNone(handoff.resolve_handoff(self.root, REL))


class StopHookTests(_Workspace):
    def payload(self, **overrides):
        base = {
            "hook_event_name": "SubagentStop",
            "agent_type": "gh-create-issue",
            "last_assistant_message": f"HANDOFF: {REL}\nSTATUS: DRAFT_READY\nSUMMARY: ok",
        }
        base.update(overrides)
        return base

    def test_displays_handoff_body_via_system_message(self):
        self.write_handoff("# draft\n本文テキスト")
        code, out, _ = self.run_hook(stop, self.payload())
        self.assertEqual(code, 0)
        message = json.loads(out)["systemMessage"]
        self.assertIn("本文テキスト", message)
        self.assertIn(REL, message)
        self.assertNotIn("decision", json.loads(out))

    def test_other_agent_type_is_silent(self):
        self.write_handoff()
        for agent in ("pr-reviewer", "", None):
            with self.subTest(agent=agent):
                payload = self.payload()
                payload["agent_type"] = agent
                code, out, _ = self.run_hook(stop, payload)
                self.assertEqual((code, out), (0, ""))

    def test_missing_or_unreadable_handoff_is_silent_with_evidence(self):
        code, out, err = self.run_hook(stop, self.payload())
        self.assertEqual((code, out), (0, ""))
        self.assertIn("HANDOFF_UNREADABLE", err)
        code, out, err = self.run_hook(stop, self.payload(last_assistant_message="done"))
        self.assertEqual((code, out), (0, ""))
        self.assertIn("NO_HANDOFF_LINE", err)

    def test_large_handoff_is_truncated(self):
        self.write_handoff("a" * (handoff.MAX_DISPLAY_BYTES + 10))
        _, out, _ = self.run_hook(stop, self.payload())
        self.assertIn("切詰め", json.loads(out)["systemMessage"])

    def test_unparsable_stdin_is_silent(self):
        stdout = io.StringIO()
        code = stop.run(
            stdin=io.StringIO("not json"), stdout=stdout, stderr=io.StringIO(),
            project_root=self.root,
        )
        self.assertEqual((code, stdout.getvalue()), (0, ""))


@unittest.skipUnless(shutil.which("bash"), "bash required")
class LauncherTests(unittest.TestCase):
    def run_launcher(self, name, payload):
        env = {**os.environ, "CLAUDE_PROJECT_DIR": str(ROOT)}
        return subprocess.run(
            ["bash", str(HOOK_DIR / name)], input=json.dumps(payload), text=True,
            capture_output=True, env=env, cwd=tempfile.gettempdir(), check=False,
        )

    def test_stop_launcher_is_silent_for_out_of_scope_agent(self):
        result = self.run_launcher("subagent-draft-display.sh", {"agent_type": "pr-reviewer"})
        self.assertEqual((result.returncode, result.stdout), (0, ""))


class RegistrationTests(unittest.TestCase):
    def setUp(self):
        self.hooks = json.loads((ROOT / ".claude/settings.json").read_text("utf-8"))["hooks"]

    def commands(self, event, matcher):
        return [
            hook["command"]
            for entry in self.hooks[event] if entry.get("matcher") == matcher
            for hook in entry["hooks"]
        ]

    def test_subagent_stop_displays_for_gh_create_issue(self):
        commands = self.commands("SubagentStop", "gh-create-issue")
        self.assertEqual(len(commands), 1)
        self.assertIn("subagent-draft-display.sh", commands[0])

    def test_no_post_tool_use_hook_is_registered_for_the_draft_display(self):
        for entry in self.hooks["PostToolUse"]:
            for hook in entry["hooks"]:
                self.assertNotIn("subagent-draft", hook["command"])


class AgentAssetTests(unittest.TestCase):
    def frontmatter(self):
        lines = (ROOT / ".claude/agents/gh-create-issue.md").read_text("utf-8").splitlines()
        end = lines.index("---", 1)
        return dict(line.split(": ", 1) for line in lines[1:end] if ": " in line)

    def test_agent_has_no_delegation_or_edit_tools(self):
        tools = {tool.strip() for tool in self.frontmatter()["tools"].split(",")}
        self.assertEqual(tools, {"Read", "Write", "Grep", "Glob", "Bash"})

    def test_skill_wrapper_delegates_to_the_agent_only(self):
        skill = (ROOT / ".claude/skills/gh-create-issue/SKILL.md").read_text("utf-8")
        self.assertIn("../../agents/gh-create-issue.md", skill)
        self.assertIn("subagent_type: gh-create-issue", skill)


if __name__ == "__main__":
    unittest.main()
