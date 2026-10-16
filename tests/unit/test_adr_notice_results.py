"""実shell書込結果とdurable通知索引による3tool E2E。"""
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from adr.hook import notification
from adr.notice_roots import PREFIX
from adr.schema import ADR_SPEC
from adr.store import write
from feedback_ledger.tomlwrite import dumps
from tests.unit.test_adr import draft

ROOT = Path(__file__).resolve().parents[2]
TOOLS = ("Bash", "mcp__plugin_context-mode_context-mode__ctx_execute",
         "mcp__plugin_context-mode_context-mode__ctx_batch_execute")


class AdrNoticeResultTest(unittest.TestCase):
    def test_real_shell_writes_notify_without_command_inference(self):
        scripts = ("{ cd tool; W; }", "if true; then cd tool; fi; W",
                   "for x in 1; do cd tool; W; done",
                   "while true; do cd tool; W; break; done",
                   "case x in x) cd tool; W;; esac", "pushd tool; W; popd",
                   "(cd tool; W)", "(cd tool; W) | cat", "(cd tool; W) & wait",
                   'cd tool; printf "%s" "("; cd ..; W', "cd tool; cd -; W")
        for script in scripts:
            with self.subTest(script=script), tempfile.TemporaryDirectory() as temporary:
                repo = Path(temporary)
                (repo / ".git").mkdir()
                (repo / "tool/adr").mkdir(parents=True)
                (repo / "adr").mkdir()
                expected_root = repo / ("adr" if "cd .." in script or "cd -;" in script
                                        else "tool/adr")
                other_root = repo / ("tool/adr" if expected_root == repo / "adr" else "adr")
                write(other_root, draft("unrelated"))
                source = repo / "draft.toml"
                source.write_text(dumps(ADR_SPEC, draft("written")))
                writer = f'python3 -m adr new-entry --root adr --draft "{source}"'
                command = script.replace("W", writer)
                result = subprocess.run(["bash", "-c", command], cwd=repo, text=True,
                    capture_output=True, env=dict(os.environ, PYTHONPATH=str(ROOT)), timeout=10)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertTrue((expected_root / (draft("written")["id"] + ".toml")).exists())
                for tool in TOOLS:
                    for response in (result.stdout, {"content": [{"text": result.stdout}]},
                                     "[output truncated]", None):
                        payload = dict(tool_name=tool, cwd=str(repo), tool_response=response,
                                       tool_input={"command": command, "code": command,
                                                   "commands": [{"command": command}]})
                        output = subprocess.run(["bash", str(ROOT / ".codex/hooks/adr-notify.sh")],
                            input=json.dumps(payload), text=True, capture_output=True, timeout=10)
                        self.assertEqual(output.returncode, 0, output.stderr)
                        message = json.loads(output.stdout)["systemMessage"]
                        self.assertIn(draft("written")["id"], message)
                        self.assertNotIn(draft("unrelated")["id"], message)

    def test_untrusted_response_cannot_choose_roots_or_hide_partial_receipts(self):
        from adr.notice_roots import register_root
        with tempfile.TemporaryDirectory() as temporary:
            repo = Path(temporary)
            for name in ("first", "second", "unregistered"):
                write(repo / name, draft(name))
                if name != "unregistered":
                    register_root(repo / name, repo)
            broken = repo / "broken"
            broken.mkdir()
            (broken / "invalid.toml").write_text("invalid TOML")
            register_root(broken, repo)
            for response in (PREFIX + json.dumps(str(repo / "unregistered")),
                             PREFIX + json.dumps(str(repo / "first")), PREFIX + "invalid"):
                message = notification(dict(tool_name="Bash", cwd=str(repo),
                                            tool_response=response))["systemMessage"]
                self.assertIn(draft("first")["id"], message)
                self.assertIn(draft("second")["id"], message)
                self.assertNotIn(draft("unregistered")["id"], message)
            self.assertEqual(notification(dict(tool_name="Read", cwd=str(repo))), {})
