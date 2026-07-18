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


def _assert_manifest_contract(text):
    """Codex interface manifest の明示起動契約を fail-close に検証する。"""
    interface = _top_level_mapping_block(text, "interface")
    policy = _top_level_mapping_block(text, "policy")
    if interface is None:
        raise AssertionError("interface mapping is missing")
    if policy is None:
        raise AssertionError("policy mapping is missing")

    prompt_keys = list(re.finditer(r"(?m)^  default_prompt\s*:", interface))
    if len(prompt_keys) != 1:
        raise AssertionError("interface.default_prompt must be defined exactly once")

    prompts = list(
        re.finditer(
            r'(?m)^  default_prompt:\s*(["\'])(?P<value>[^\n]*)\1\s*$',
            interface,
        )
    )
    if len(prompts) != 1:
        raise AssertionError("interface.default_prompt must be quoted and well-formed")
    if re.search(
        r"(?<![\w$-])\$worktree-publish(?![\w-])",
        prompts[0].group("value"),
    ) is None:
        raise AssertionError(
            "interface.default_prompt must contain the complete token "
            "'$worktree-publish'"
        )

    invocation_key_pattern = re.compile(
        r"(?m)^(?P<indent> *)allow_implicit_invocation\s*:"
    )
    definitions = list(invocation_key_pattern.finditer(text))
    if len(definitions) != 1:
        raise AssertionError(
            "allow_implicit_invocation must be defined exactly once"
        )

    invocation_value_pattern = re.compile(
        r"(?m)^(?P<indent> *)allow_implicit_invocation:\s*"
        r"(?P<value>[^\s#]+)\s*(?:#.*)?$"
    )
    values = list(invocation_value_pattern.finditer(text))
    policy_definitions = list(invocation_key_pattern.finditer(policy))
    if len(policy_definitions) != 1 or definitions[0].group("indent") != "  ":
        raise AssertionError(
            "allow_implicit_invocation must be defined directly under policy"
        )
    if len(values) != 1:
        raise AssertionError("allow_implicit_invocation must be well-formed")
    if values[0].group("value") != "false":
        raise AssertionError("allow_implicit_invocation must be false")


class WorktreePublishManifestTests(unittest.TestCase):
    def test_codex_interface_manifest_requires_explicit_invocation(self):
        manifest = SKILL_DIR / "agents" / "openai.yaml"
        self.assertTrue(manifest.is_file(), f"manifest not found: {manifest}")

        _assert_manifest_contract(manifest.read_text(encoding="utf-8"))

    def test_rejects_longer_skill_name_in_default_prompt(self):
        text = """\
interface:
  default_prompt: "Use $worktree-publisher to publish the worktree."
policy:
  allow_implicit_invocation: false
"""

        with self.assertRaisesRegex(AssertionError, "complete token"):
            _assert_manifest_contract(text)

    def test_rejects_duplicate_allow_implicit_invocation_definitions(self):
        text = """\
interface:
  default_prompt: "Use $worktree-publish to publish the worktree."
policy:
  allow_implicit_invocation: false
  allow_implicit_invocation: true
"""

        with self.assertRaisesRegex(AssertionError, "defined exactly once"):
            _assert_manifest_contract(text)


if __name__ == "__main__":
    unittest.main()
