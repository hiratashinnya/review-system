import datetime as dt
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[2]
SERVER = ROOT / ".codex" / "mcp" / "claude_review" / "server.py"
SPEC = importlib.util.spec_from_file_location("claude_review_mcp_server", SERVER)
server = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(server)


class Completed:
    def __init__(self, args, stdout="", stderr="", returncode=0):
        self.args = args
        self.stdout = stdout
        self.stderr = stderr
        self.returncode = returncode


class ClaudeReviewMcpTests(unittest.TestCase):
    def test_model_default_and_validation(self):
        self.assertEqual(server.validate_model(None), "opus")
        self.assertEqual(server.validate_model("fable"), "fable")
        with self.assertRaises(server.ToolError):
            server.validate_model("sonnet")

    def test_claude_command_is_read_only(self):
        command = server.build_claude_command("review this", "fable")
        self.assertIn("--permission-mode", command)
        self.assertIn("plan", command)
        self.assertIn("--tools", command)
        self.assertIn("Read,Glob,Grep,LS", command)
        self.assertIn("--fallback-model", command)
        self.assertIn("opus", command)
        forbidden = " ".join(command).lower()
        for token in ("edit", "write", "bash", "bypass", "danger", "acceptedits"):
            self.assertNotIn(token, forbidden)

    def test_pr_context_uses_gh_view_and_diff(self):
        calls = []

        def fake_run(args, cwd, timeout_s):
            calls.append(args)
            if args[:3] == ["gh", "pr", "view"]:
                return Completed(args, stdout='{"number":1,"title":"T"}')
            if args[:3] == ["gh", "pr", "diff"]:
                return Completed(args, stdout="diff --git a/x b/x")
            raise AssertionError(args)

        with mock.patch.object(server, "run_command", side_effect=fake_run):
            text = server.pr_context(1, "/tmp/work")

        self.assertIn("gh pr view", text)
        self.assertIn("gh pr diff", text)
        self.assertIn('"title":"T"', text)
        self.assertIn("diff --git", text)
        self.assertEqual(calls[0][:4], ["gh", "pr", "view", "1"])
        self.assertEqual(calls[1][:4], ["gh", "pr", "diff", "1"])

    def test_rate_limit_preflight_blocks_future_reset(self):
        with tempfile.TemporaryDirectory() as tmp:
            state_root = Path(tmp)
            reset_at = (dt.datetime.now().astimezone() + dt.timedelta(hours=1)).isoformat()
            state_path = state_root / "claude-review-mcp" / "rate-limit.json"
            state_path.parent.mkdir(parents=True)
            state_path.write_text(json.dumps({"error": "rate_limit", "reset_at": reset_at}))
            with mock.patch.dict(server.os.environ, {"XDG_STATE_HOME": str(state_root)}):
                blocked, reason = server.current_block()
        self.assertTrue(blocked)
        self.assertIn("rate-limit block active", reason)

    def test_rate_limit_preflight_prefers_structured_reset_at(self):
        with tempfile.TemporaryDirectory() as tmp:
            state_root = Path(tmp)
            last_seen_at = (dt.datetime.now().astimezone() - dt.timedelta(hours=1)).isoformat()
            reset_at = (dt.datetime.now().astimezone() + dt.timedelta(hours=1)).replace(microsecond=0).isoformat()
            state_path = state_root / "claude-review-mcp" / "rate-limit.json"
            state_path.parent.mkdir(parents=True)
            state_path.write_text(
                json.dumps(
                    {
                        "error": "rate_limit",
                        "last_seen_at": last_seen_at,
                        "reset_at": reset_at,
                        "raw": "rate limit encountered",
                    }
                )
            )
            with mock.patch.dict(server.os.environ, {"XDG_STATE_HOME": str(state_root)}):
                blocked, reason = server.current_block()
        self.assertTrue(blocked)
        self.assertIn(reset_at, reason)

    def test_tools_list_contains_two_tools(self):
        response = server.handle_request({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
        names = [tool["name"] for tool in response["result"]["tools"]]
        self.assertEqual(names, ["claude_review", "claude_review_status"])

    def test_claude_review_builds_prompt_and_command_without_live_call(self):
        commands = []

        def fake_run(args, cwd, timeout_s):
            commands.append(args)
            if args[:3] == ["gh", "pr", "view"]:
                return Completed(args, stdout='{"number":2}')
            if args[:3] == ["gh", "pr", "diff"]:
                return Completed(args, stdout="diff body")
            if args[0] == "claude":
                return Completed(args, stdout=json.dumps({"result": "ok"}))
            raise AssertionError(args)

        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.dict(server.os.environ, {"XDG_STATE_HOME": tmp}, clear=False):
                with mock.patch.object(server, "run_command", side_effect=fake_run):
                    with mock.patch.object(server, "current_block", return_value=(False, "ok")):
                        result = server.claude_review(
                            {
                                "prompt": "review",
                                "model": "opus",
                                "pr_number": 2,
                                "workspace": "/tmp/work",
                            }
                        )

        self.assertEqual(result, "ok")
        claude_command = commands[-1]
        self.assertEqual(claude_command[0], "claude")
        self.assertIn("--no-session-persistence", claude_command)
        self.assertIn("GitHub PR Context #2", claude_command[2])


if __name__ == "__main__":
    unittest.main()
