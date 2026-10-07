import json
from pathlib import Path
import tomllib
import unittest


ROOT = Path(__file__).resolve().parents[2]


class NativeMergePermissionTests(unittest.TestCase):
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
