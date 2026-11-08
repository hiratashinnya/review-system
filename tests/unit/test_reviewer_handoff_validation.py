"""handoff ヘッダとファイル名の厳密な一致。"""

import tempfile
import unittest
from pathlib import Path

from karte.handoff_header import HEADER_RE
from karte.handoff_path import resolve_reviewer_handoff
from karte.path_errors import KartePathError


class TestHandoffValidation(unittest.TestCase):
    def test_handoff_path_requires_exact_directory_and_filename(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for target, reason in (
                ("docs/_handoff/pr-reviewer--k.md", "直下ではない"),
                ("tmp/x/_handoff/pr-reviewer--k.md", "直下ではない"),
                ("tmp/_handoff/pr-reviewer--a b.md", "ファイル名が"),
                ("tmp/_handoff/pr-reviewer--a;b.md", "ファイル名が"),
                ("tmp/_handoff/pr-reviewer--a$(b).md", "ファイル名が"),
                ("tmp/_handoff/pr-reviewer--日本.md", "ファイル名が"),
                ("tmp/_handoff/pr-reviewer---x.md", "ファイル名が"),
                ("tmp/_handoff/pr-reviewer--_x.md", "ファイル名が"),
                ("tmp/_handoff/pr-reviewer--.x.md", "ファイル名が"),
                ("tmp/_handoff/pr-reviewer--.md", "ファイル名が"),
            ):
                with self.subTest(target=target), self.assertRaisesRegex(KartePathError, reason):
                    resolve_reviewer_handoff(root / target, root)
            target = root / "tmp/_handoff/pr-reviewer--A0._-z.md"
            self.assertEqual(target, resolve_reviewer_handoff(target, root))

    def test_header_pattern_rejects_trailing_newline(self):
        valid = "<!-- handoff issue=1 round=1 -->"
        self.assertIsNotNone(HEADER_RE.fullmatch(valid))
        self.assertIsNone(HEADER_RE.fullmatch(valid + "\n"))

    def test_filename_rejects_trailing_newline(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "tmp/_handoff/pr-reviewer--x.md\n"
            with self.assertRaisesRegex(KartePathError, "ファイル名が"):
                resolve_reviewer_handoff(target, root)


if __name__ == "__main__":
    unittest.main()
