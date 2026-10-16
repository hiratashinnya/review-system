"""shellプロセス境界をまたぐ通知のcwdを検証する。"""
import tempfile
import unittest
from pathlib import Path
from adr.hook import notification
from adr.notice_roots import register_root
from adr.shell_commands import command_roots
from adr.store import write
from tests.unit.test_adr import draft


class AdrShellScopeTest(unittest.TestCase):
    def test_parent_and_nested_subshell_pipeline_cwds(self):
        with tempfile.TemporaryDirectory() as temporary:
            repo = Path(temporary)
            (repo / "tool" / "nested").mkdir(parents=True)
            write(repo / "adr", draft())
            register_root(repo / "adr", repo)
            writer = "python3 -m adr new-entry --root adr --draft x"
            commands = (f"(cd tool); {writer}", f"cd tool | cat; {writer}",
                        f"cat | cd tool; {writer}", f"(cd tool | cat); {writer}",
                        f"(cd tool; (cd nested)); {writer}", f"cd tool & {writer}")
            for command in commands:
                self.assertEqual(command_roots(command, repo), {repo / "adr"})
                routes = (("Bash", {"command": command}),
                          ("mcp__plugin_context-mode_context-mode__ctx_execute", {"code": command}),
                          ("mcp__plugin_context-mode_context-mode__ctx_batch_execute",
                           {"commands": [{"command": command}]}))
                for tool, inputs in routes:
                    with self.subTest(command=command, tool=tool):
                        result = notification(dict(tool_name=tool, cwd=str(repo), tool_input=inputs))
                        self.assertIn(draft()["id"], result["systemMessage"])
            inner_commands = {
                f"(cd tool; {writer}); {writer}": {repo / "tool/adr", repo / "adr"},
                f"(cd tool; {writer}) | cat; {writer}": {repo / "tool/adr", repo / "adr"},
                f"cd tool; (cd nested; {writer}); {writer}":
                    {repo / "tool/nested/adr", repo / "tool/adr"},
                f"(cd tool; (cd nested; {writer}); {writer})":
                    {repo / "tool/nested/adr", repo / "tool/adr"},
            }
            for command, expected in inner_commands.items():
                with self.subTest(command=command):
                    self.assertEqual(command_roots(command, repo), expected)

    def test_subshell_write_notifies_its_own_root(self):
        with tempfile.TemporaryDirectory() as temporary:
            repo = Path(temporary)
            write(repo / "tool/adr", draft())
            register_root(repo / "tool/adr", repo)
            command = "(cd tool && python3 -m adr file-issue --root=adr --id x); echo done"
            result = notification(dict(tool_name="Bash", cwd=str(repo), tool_input={"command": command}))
            self.assertIn(draft()["id"], result["systemMessage"])
