"""asset_parity の inline 判定が使う marker 書式が guidance_sync の生成物と一致し続けること。

marker の書き手は `guidance_sync.sync._principles_marker` だけで、書式は asset_parity 側に
複製されている（import 結合を避けるため）。複製の食い違いは、実在する inline 済み原則を
MISSING と誤判定する形（または不完全な行を inline 済みと誤認する形）で現れるので、
ここで機械的に固定する。

生成物は先頭の生成ヘッダー（最初の空行まで）にも同じ marker 行を必ず書く。inline 済みの
証拠になるのは本文側の marker だけなので、ヘッダー／本文の境界の形も実際の
`rendered_bytes` で固定する（asset_parity は境界の形を複製して持つ）。
"""

import tempfile
import unittest
from pathlib import Path

from asset_parity.copilot_paths import copilot_instructions_path
from asset_parity.inlining import is_inlined_into_copilot_instructions, principles_marker_pattern
from asset_parity.inventory import MODE_PRINCIPLE, SKILL, Asset
from guidance_sync.sync import (
    COMMON_SOURCE,
    PRINCIPLES_MARKER_RE,
    PRINCIPLES_SOURCE,
    TARGETS,
    _principles_marker,
    rendered_bytes,
)
from tests.unit.asset_parity_fixtures import generated_instructions_text

SKILL_NAME = "spec-principles"
# The file asset_parity reads (from its single path definition); pinned to guidance_sync's target.
INSTRUCTIONS_RELATIVE_PATH = copilot_instructions_path(Path(".")).as_posix()


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

    def _write_real_render(self, root: Path, *, common: bytes) -> str:
        """Write the file guidance_sync really renders for the Copilot target; return its text."""
        sources = {
            COMMON_SOURCE: common,
            PRINCIPLES_SOURCE: b"principles body",
            TARGETS[INSTRUCTIONS_RELATIVE_PATH]: b"# copilot\n",
        }
        rendered = rendered_bytes(INSTRUCTIONS_RELATIVE_PATH, load=sources.__getitem__)
        instructions = root / INSTRUCTIONS_RELATIVE_PATH
        instructions.parent.mkdir(parents=True)
        instructions.write_bytes(rendered)
        return rendered.decode("utf-8")

    def test_real_render_with_marker_in_common_body_is_recognised_as_inlined(self):
        # the real common guidance carries its own marker line in its principles section
        common = b"# common\n\n" + _principles_marker(b"principles body") + b"\n"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_real_render(root, common=common)
            self.assertTrue(is_inlined_into_copilot_instructions(_asset(root), root))

    def test_real_render_without_marker_in_body_has_header_marker_but_is_not_inlined(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            text = self._write_real_render(root, common=b"# common\n")
            # the generator itself puts the complete marker in the header ...
            self.assertIn(_rendered(), text.splitlines()[:5])
            # ... and that alone must not read as inlined
            self.assertFalse(is_inlined_into_copilot_instructions(_asset(root), root))

    def test_marker_without_header_body_split_is_not_recognised_as_inlined(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            instructions = root / INSTRUCTIONS_RELATIVE_PATH
            instructions.parent.mkdir(parents=True)
            instructions.write_text(_rendered() + "\n", encoding="utf-8")
            self.assertFalse(is_inlined_into_copilot_instructions(_asset(root), root))

    def test_prefix_only_marker_in_body_is_not_recognised_as_inlined(self):
        prefix = f"<!-- principles-source: {PRINCIPLES_SOURCE};"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            instructions = root / INSTRUCTIONS_RELATIVE_PATH
            instructions.parent.mkdir(parents=True)
            instructions.write_text(
                generated_instructions_text(header_skill=SKILL_NAME, body_lines=(prefix,)),
                encoding="utf-8",
            )
            self.assertFalse(is_inlined_into_copilot_instructions(_asset(root), root))


if __name__ == "__main__":
    unittest.main()
