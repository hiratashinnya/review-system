"""worktree-publish skill の Codex interface manifest 契約を検証する。"""

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SKILL_DIR = ROOT / ".agents" / "skills" / "worktree-publish"


def _top_level_mapping_block(text, key):
    """汎用 YAML 依存を追加せず、この manifest の2-space mapping だけを切り出す。"""
    match = re.search(
        rf"(?ms)^{re.escape(key)}:\s*\n(?P<body>(?:^[ ]+[^\n]*(?:\n|$))*)",
        text,
    )
    if match is None:
        return None
    return match.group("body")


class WorktreePublishManifestTests(unittest.TestCase):
    def test_codex_interface_manifest_requires_explicit_invocation(self):
        manifest = SKILL_DIR / "agents" / "openai.yaml"
        self.assertTrue(manifest.is_file(), f"manifest not found: {manifest}")

        text = manifest.read_text(encoding="utf-8")
        interface = _top_level_mapping_block(text, "interface")
        policy = _top_level_mapping_block(text, "policy")
        self.assertIsNotNone(interface, "interface mapping is missing")
        self.assertIsNotNone(policy, "policy mapping is missing")

        prompt = re.search(
            r'(?m)^  default_prompt:\s*(["\'])(?P<value>[^\n]*)\1\s*$',
            interface,
        )
        self.assertIsNotNone(prompt, "interface.default_prompt is missing or malformed")
        self.assertIn("$worktree-publish", prompt.group("value"))
        self.assertRegex(
            policy,
            r"(?m)^  allow_implicit_invocation:\s*false\s*$",
        )


if __name__ == "__main__":
    unittest.main()
