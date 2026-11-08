"""karte-notify.sh の stdin 事前フィルタは ``TRIGGER_RE`` の偽陰性を生まない（Issue #375 R4）。

スクリプトは ``python3 -m karte_notify.hook`` を起動するかどうかだけを決める。本物の hook の代わりに
マーカーを出すだけの偽モジュールを置いた一時プロジェクトで、起動の有無を実測する。
"""

import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / ".claude/hooks/karte-notify.sh"
MARKER = "HOOK-RAN"


class TestPrefilter(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="karte-notify-")).resolve()
        self.addCleanup(lambda: shutil.rmtree(self.root, ignore_errors=True))
        package = self.root / "karte_notify"
        package.mkdir()
        (package / "__init__.py").write_text("", encoding="utf-8")
        (package / "hook.py").write_text(f"print({MARKER!r})\n", encoding="utf-8")

    def _ran(self, command):
        payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": command}})
        env = {**os.environ, "CLAUDE_PROJECT_DIR": str(self.root)}
        done = subprocess.run(
            ["bash", str(SCRIPT)], input=payload, capture_output=True, text=True, env=env, check=False
        )
        return MARKER in done.stdout

    def test_trigger_verbs_start_the_hook_even_with_irregular_whitespace(self):
        for command in (
            "python3 -m karte decide --finding F-1-01 --scope out",
            "python3 -m karte  decide --finding F-1-01",
            "python3 -m karte\tdecide --finding F-1-01",
            "python3  -m  karte   ingest-reviewer --from x",
            "python3 -m karte close-attempt --outcome fixed",
        ):
            with self.subTest(command=command):
                self.assertTrue(self._ran(command))

    def test_codex_reviewer_wrappers_start_the_hook(self):
        for command in (
            "python3 -m codex_worktree_exec --role pr-reviewer -C wt",
            "python3 -m issue_start.readonly_workspace --role pr-reviewer -C wt",
        ):
            with self.subTest(command=command):
                self.assertTrue(self._ran(command))

    def test_unrelated_commands_do_not_start_the_hook(self):
        self.assertFalse(self._ran("git status"))
        self.assertFalse(self._ran("python3 -m karte render --issue 1"))

    def test_a_trigger_word_without_karte_does_not_start_the_hook(self):
        for command in ("git log --grep decide", "echo ingest-review", "grep close-attempt notes.md"):
            with self.subTest(command=command):
                self.assertFalse(self._ran(command))


if __name__ == "__main__":
    unittest.main()
