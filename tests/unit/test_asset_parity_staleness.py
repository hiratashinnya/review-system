"""asset_parity.staleness — last-commit gap / 行数比フラグの契約（git 呼び出しは注入で隔離）。"""

import tempfile
import unittest
from pathlib import Path

from asset_parity import staleness


class TestCompare(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)

    def _write(self, rel: str, n_lines: int) -> Path:
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        text = "" if n_lines == 0 else "\n".join(f"line {i}" for i in range(n_lines)) + "\n"
        p.write_text(text, encoding="utf-8")
        return p

    def test_no_flag_when_close_in_time_and_size(self):
        canon = self._write("canon.md", 20)
        mirror = self._write("mirror.md", 22)
        epochs = {str(canon): 1_000_000, str(mirror): 1_000_100}
        result = staleness.compare(canon, mirror, self.root,
                                   commit_epoch_fn=lambda p, r: epochs[str(p)])
        self.assertFalse(result.flagged)

    def test_flags_large_day_gap(self):
        canon = self._write("canon.md", 20)
        mirror = self._write("mirror.md", 20)
        gap_seconds = 60 * 86400
        epochs = {str(canon): 1_000_000 + gap_seconds, str(mirror): 1_000_000}
        result = staleness.compare(canon, mirror, self.root, day_threshold=30,
                                   commit_epoch_fn=lambda p, r: epochs[str(p)])
        self.assertTrue(result.flagged)
        self.assertTrue(any("last-commit gap" in r for r in result.flag_reasons))

    def test_flags_large_size_ratio(self):
        canon = self._write("canon.md", 100)
        mirror = self._write("mirror.md", 10)
        result = staleness.compare(canon, mirror, self.root, size_ratio_threshold=2.0,
                                   commit_epoch_fn=lambda p, r: None)
        self.assertTrue(result.flagged)
        self.assertTrue(any("size ratio" in r for r in result.flag_reasons))
        self.assertAlmostEqual(result.size_ratio, 10.0, places=1)

    def test_no_git_history_is_fail_soft_not_error(self):
        canon = self._write("canon.md", 20)
        mirror = self._write("mirror.md", 20)
        result = staleness.compare(canon, mirror, self.root, commit_epoch_fn=lambda p, r: None)
        self.assertIsNone(result.parity_seed_epoch)
        self.assertIsNone(result.canonical_epoch)
        self.assertEqual(result.canonical_lines, result.parity_seed_lines)
        self.assertIsNone(result.day_gap)
        self.assertFalse(result.flagged)

    def test_empty_file_flagged(self):
        canon = self._write("canon.md", 0)
        mirror = self._write("mirror.md", 20)
        result = staleness.compare(canon, mirror, self.root, commit_epoch_fn=lambda p, r: None)
        self.assertTrue(result.flagged)
        self.assertIn("empty file on one side", result.flag_reasons)

    def test_deprecated_compare_keyword_remains_compatible(self):
        seed = self._write("seed.md", 20)
        mirror = self._write("mirror.md", 20)
        result = staleness.compare(
            canonical_path=seed,
            mirror_path=mirror,
            root=self.root,
            commit_epoch_fn=lambda p, r: None,
        )
        self.assertEqual(result.parity_seed_lines, 20)
        same = staleness.compare(
            parity_seed_path=seed,
            canonical_path=seed,
            mirror_path=mirror,
            root=self.root,
            commit_epoch_fn=lambda p, r: None,
        )
        self.assertEqual(same.parity_seed_lines, 20)

    def test_conflicting_compare_path_names_fail_closed(self):
        seed = self._write("seed.md", 20)
        old_seed = self._write("old-seed.md", 20)
        mirror = self._write("mirror.md", 20)
        with self.assertRaisesRegex(TypeError, "disagree"):
            staleness.compare(
                parity_seed_path=seed,
                canonical_path=old_seed,
                mirror_path=mirror,
                root=self.root,
            )

    def test_deprecated_stale_signal_constructor_keywords_remain_compatible(self):
        legacy = staleness.StaleSignal(
            canonical_epoch=1,
            mirror_epoch=2,
            day_gap=0.0,
            canonical_lines=3,
            mirror_lines=4,
            size_ratio=4 / 3,
            flagged=False,
            flag_reasons=(),
        )
        self.assertEqual(legacy.parity_seed_epoch, 1)
        self.assertEqual(legacy.parity_seed_lines, 3)
        same = staleness.StaleSignal(
            parity_seed_epoch=1,
            canonical_epoch=1,
            mirror_epoch=2,
            day_gap=0.0,
            parity_seed_lines=3,
            canonical_lines=3,
            mirror_lines=4,
            size_ratio=4 / 3,
            flagged=False,
            flag_reasons=(),
        )
        self.assertEqual(same.parity_seed_lines, 3)

    def test_conflicting_stale_signal_names_fail_closed(self):
        with self.assertRaisesRegex(TypeError, "disagree"):
            staleness.StaleSignal(
                parity_seed_epoch=1,
                canonical_epoch=2,
                mirror_epoch=2,
                day_gap=0.0,
                parity_seed_lines=3,
                canonical_lines=4,
                mirror_lines=4,
                size_ratio=1.0,
                flagged=False,
                flag_reasons=(),
            )

    def test_git_last_commit_epoch_returns_none_outside_git_repo(self):
        canon = self._write("canon.md", 5)
        # tmp ディレクトリは git 管理外 → subprocess は非0/空を返し None にフォールバック
        result = staleness.git_last_commit_epoch(canon, self.root)
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
