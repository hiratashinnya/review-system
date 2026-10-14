"""asset_parity の inline 判定が使う marker 書式が guidance_sync の生成物と一致し続けること。

marker の書き手は `guidance_sync.sync._principles_marker` だけで、書式は asset_parity 側に
複製されている（import 結合を避けるため）。複製の食い違いは、実在する inline 済み原則を
MISSING と誤判定する形（または不完全な行を inline 済みと誤認する形）で現れるので、
ここで機械的に固定する。
"""

import tempfile
import unittest
from pathlib import Path

from asset_parity.inlining import is_inlined_into_copilot_instructions, principles_marker_pattern
from asset_parity.inventory import MODE_PRINCIPLE, SKILL, Asset
from guidance_sync.sync import (
    PRINCIPLES_MARKER_RE,
    PRINCIPLES_SOURCE,
    TARGETS,
    _principles_marker,
)

SKILL_NAME = "spec-principles"
# asset_parity/copilot_paths.py rebuilds this path from parts; pinned to guidance_sync's target.
INSTRUCTIONS_RELATIVE_PATH = ".github/copilot-instructions.md"


def _rendered() -> str:
    return _principles_marker(b"principles body").decode("utf-8")


def _asset(root: Path) -> Asset:
    return Asset(SKILL_NAME, SKILL, MODE_PRINCIPLE, root / "seed.md")


class TestMarkerFormat(unittest.TestCase):
    def test_pattern_matches_whole_guidance_sync_marker(self):
        rendered = _rendered()
        self.assertIsNotNone(principles_marker_pattern(SKILL_NAME).fullmatch(rendered), rendered)

    def test_pattern_and_guidance_sync_regex_agree_on_rendered_marker(self):
        rendered = _rendered()
        self.assertIsNotNone(PRINCIPLES_MARKER_RE.search(rendered.encode("utf-8")))
        self.assertIsNotNone(principles_marker_pattern(SKILL_NAME).fullmatch(rendered))

    def test_pattern_rejects_truncated_prefix_of_rendered_marker(self):
        rendered = _rendered()
        pattern = principles_marker_pattern(SKILL_NAME)
        # every proper prefix of the generated line is an incomplete marker
        for length in range(len(rendered)):
            with self.subTest(length=length):
                self.assertIsNone(pattern.fullmatch(rendered[:length]))

    def test_guidance_sync_source_is_the_skill_asset_parity_expects(self):
        self.assertEqual(PRINCIPLES_SOURCE, f".ai/skills/{SKILL_NAME}/SKILL.md")

    def test_instructions_path_is_a_guidance_sync_target(self):
        self.assertIn(INSTRUCTIONS_RELATIVE_PATH, TARGETS)

    def test_rendered_marker_is_recognised_as_inlined(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            instructions = root / INSTRUCTIONS_RELATIVE_PATH
            instructions.parent.mkdir(parents=True)
            instructions.write_text(_rendered() + "\n", encoding="utf-8")
            self.assertTrue(is_inlined_into_copilot_instructions(_asset(root), root))

    def test_prefix_only_marker_is_not_recognised_as_inlined(self):
        prefix = f"<!-- principles-source: {PRINCIPLES_SOURCE};"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            instructions = root / INSTRUCTIONS_RELATIVE_PATH
            instructions.parent.mkdir(parents=True)
            instructions.write_text(prefix + "\n", encoding="utf-8")
            self.assertFalse(is_inlined_into_copilot_instructions(_asset(root), root))


if __name__ == "__main__":
    unittest.main()
