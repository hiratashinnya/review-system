"""`governance-directives.md` の synced-from marker が `CLAUDE.md` に追従しているかの機械検査。

CLAUDE.md 冒頭の規定：中核規範は毎ターン注入され、その配送用の写しが
`.claude/hooks/governance-directives.md`。**正本は CLAUDE.md** で、規約を変えたら写しも合わせる。
追従漏れは `.claude/hooks/check-governance-drift.sh`（PostToolUse）が検知する——が、同フックは
**常に exit 0 の fail-open な nag** であり、かつ発火条件が
`realpath(edited) == realpath($CLAUDE_PROJECT_DIR/CLAUDE.md)` なので、linked worktree 側の
CLAUDE.md を編集した場合は沈黙する（Issue #323 実装時に実測）。結果として「marker を更新しないまま
merge される」経路が開いたままになる。本テストはその追従を CI で fail-close にする。

依存仕様（フックと同一である必要がある）:
  - ハッシュ＝`hashlib.sha256(<repo_root>/CLAUDE.md の生バイト).hexdigest()[:12]`
  - marker＝`<!-- synced-from: CLAUDE.md@<12桁hex> -->`
  （実体＝`.claude/hooks/check-governance-drift.sh` の埋め込み python3。どちらかを変えるときは
  両方を同時に変える。）
"""

import hashlib
import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CANONICAL = REPO_ROOT / "CLAUDE.md"
DELIVERY_COPY = REPO_ROOT / ".claude" / "hooks" / "governance-directives.md"

MARKER_RE = re.compile(r"<!--\s*synced-from:\s*CLAUDE\.md@([0-9a-f]{12})\s*-->")


class TestGovernanceDirectivesSyncMarker(unittest.TestCase):
    """写しの marker が正本 CLAUDE.md の現在のハッシュと一致することを要求する。"""

    def test_delivery_copy_declares_a_sync_marker(self):
        self.assertTrue(
            DELIVERY_COPY.is_file(),
            f"配送用の写しが存在しない: {DELIVERY_COPY}",
        )
        text = DELIVERY_COPY.read_text(encoding="utf-8")
        self.assertIsNotNone(
            MARKER_RE.search(text),
            f"{DELIVERY_COPY} に `<!-- synced-from: CLAUDE.md@<12桁hex> -->` marker が無い。"
            " check-governance-drift.sh がこの marker を読むため、削除・改名してはならない。",
        )

    def test_marker_matches_the_current_canonical_hash(self):
        expected = hashlib.sha256(CANONICAL.read_bytes()).hexdigest()[:12]
        match = MARKER_RE.search(DELIVERY_COPY.read_text(encoding="utf-8"))
        assert match is not None  # 直前のテストが本体を担保する
        self.assertEqual(
            match.group(1),
            expected,
            "governance-directives.md の synced-from marker が CLAUDE.md に追従していない。\n"
            f"  期待値（現在の CLAUDE.md の sha256 先頭12桁）: {expected}\n"
            f"  記録値: {match.group(1)}\n"
            "CLAUDE.md を変更したら、同一 PR で写しの内容を突き合わせた上で marker を"
            " 上記の期待値へ更新する（CLAUDE.md 冒頭の規定）。",
        )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
