"""`governance-directives.md` の synced-from marker が**規範の正本集合**に追従しているかの機械検査。

CLAUDE.md 冒頭の規定：中核規範は毎ターン注入され、その配送用の写しが
`.claude/hooks/governance-directives.md`。**正本は `CLAUDE.md` ＋ `.claude/rules/*.md` ＋
`.ai/guidance/common.md`** で、
規約を変えたら写しも合わせる。
追従漏れは `.claude/hooks/check-governance-drift.sh`（PostToolUse）が検知する——が、同フックは
**常に exit 0 の fail-open な nag** であり、かつ発火条件が編集対象ファイルのパス一致なので、
linked worktree 側の正本を編集した場合は沈黙する（Issue #323 実装時に実測）。結果として
「marker を更新しないまま merge される」経路が開いたままになる。本テストはその追従を CI で
fail-close にする。

Issue #387（PR #383）で規範本文が `CLAUDE.md` 単体から `.claude/rules/*.md` へ分割された。
正本を `CLAUDE.md` 単体のハッシュで見張り続けると、**規範の大半を占める `.claude/rules/` 側の
変更に対してフックもテストも一切反応しない**（＝写しが黙って規範から乖離する）。そのため
ハッシュの対象を「正本集合の連結ハッシュ」へ拡張する（オーナー確定方式）。
marker の形式は従来どおり `<!-- synced-from: CLAUDE.md@<12桁hex> -->` の1行を維持する
——写し側にファイルごとの marker を並べる案は、どのファイルが drift したかを特定できる利点が
あるものの、写しの構造変更を要し注入本文を膨らませるため見送った。

依存仕様（フックと同一である必要がある）:
  - 正本集合＝`<repo_root>/CLAUDE.md` ＋ `<repo_root>/.claude/rules/*.md`（相対パス昇順）
    ＋ `<repo_root>/.ai/guidance/common.md`
  - ハッシュ＝各ファイルについて「相対パス(utf-8) + NUL + 生バイト + NUL」を順に連結した
    バイト列の `hashlib.sha256(...).hexdigest()[:12]`
    （相対パスを混ぜるのは、ファイルの分割・改名・並び替えを内容の移動と区別するため）
  - marker＝`<!-- synced-from: CLAUDE.md@<12桁hex> -->`
  （実体＝`.claude/hooks/check-governance-drift.sh` の埋め込み python3。どちらかを変えるときは
  両方を同時に変える。）

併せて、`.claude/rules/*.md` の集合と `CLAUDE.md` の `@` import 行の集合が双方向で一致することも
検査する（F-387-05）。rules を追加して `@` 行を足し忘れると、その規範は誰にも配送されないまま
何も赤くならないため。
"""

import hashlib
import json
import os
import re
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
ENTRYPOINT = REPO_ROOT / "CLAUDE.md"
RULES_DIR = REPO_ROOT / ".claude" / "rules"
RULES_GLOB = "*.md"
DELIVERY_COPY = REPO_ROOT / ".claude" / "hooks" / "governance-directives.md"

MARKER_RE = re.compile(r"<!--\s*synced-from:\s*CLAUDE\.md@([0-9a-f]{12})\s*-->")
# CLAUDE.md の import 行（例: `@.claude/rules/01-principles.md`）。
IMPORT_RE = re.compile(r"^@(\S+\.md)\s*$", re.MULTILINE)
COMMON_GUIDANCE = ".ai/guidance/common.md"


def canonical_files(root=REPO_ROOT):
    """正本集合を相対パス昇順で返す（フックの実装と同一の順序規則）。"""
    rules = sorted(
        p.relative_to(root).as_posix()
        for p in (root / ".claude" / "rules").glob(RULES_GLOB)
    )
    return ["CLAUDE.md"] + rules + [COMMON_GUIDANCE]


def canonical_hash(root=REPO_ROOT):
    """正本集合の連結ハッシュ（先頭12桁）。フックの埋め込み python3 と同一実装。"""
    digest = hashlib.sha256()
    for rel in canonical_files(root):
        digest.update(rel.encode("utf-8"))
        digest.update(b"\0")
        digest.update((root / rel).read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()[:12]


class TestGovernanceDirectivesSyncMarker(unittest.TestCase):
    """写しの marker が正本集合の現在のハッシュと一致することを要求する。"""

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

    def test_canonical_set_covers_the_rules_directory(self):
        # ハッシュ対象が CLAUDE.md 単体に戻る退行（Issue #387 の再発）を直接止める。
        files = canonical_files()
        self.assertIn("CLAUDE.md", files)
        rules = [rel for rel in files if rel.startswith(".claude/rules/")]
        self.assertTrue(
            rules,
            "`.claude/rules/*.md` が正本集合に1件も入っていない。規範本文は同ディレクトリに"
            " あるため、CLAUDE.md 単体を見張っても追従漏れを検知できない（Issue #387）。",
        )

    def test_canonical_set_includes_common_guidance(self):
        self.assertIn(
            COMMON_GUIDANCE,
            canonical_files(),
            "Claude が公式 import する common guidance も governance 正本集合へ含める。",
        )

    def test_common_guidance_bytes_change_the_canonical_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for rel in canonical_files():
                path = root / rel
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes((REPO_ROOT / rel).read_bytes())
            before = canonical_hash(root)
            common = root / COMMON_GUIDANCE
            common.write_bytes(common.read_bytes() + b"common-only-change\n")
            self.assertNotEqual(before, canonical_hash(root))

    def test_marker_matches_the_current_canonical_hash(self):
        expected = canonical_hash()
        match = MARKER_RE.search(DELIVERY_COPY.read_text(encoding="utf-8"))
        assert match is not None  # 直前のテストが本体を担保する
        self.assertEqual(
            match.group(1),
            expected,
            "governance-directives.md の synced-from marker が正本集合に追従していない。\n"
            f"  正本集合: {', '.join(canonical_files())}\n"
            f"  期待値（連結ハッシュの先頭12桁）: {expected}\n"
            f"  記録値: {match.group(1)}\n"
            "CLAUDE.md、.claude/rules/*.md、.ai/guidance/common.md のいずれかを変更したら、同一 PR で写しの内容を"
            " 突き合わせた上で marker を上記の期待値へ更新する（CLAUDE.md 冒頭の規定）。",
        )


class TestRulesImportsAreComplete(unittest.TestCase):
    """`.claude/rules/*.md` の集合と CLAUDE.md の `@` import 行が双方向一致すること（F-387-05）。

    `@` import は Claude Code がルールファイルを読み込む唯一の配線なので、rules を足して
    `@` 行を足し忘れると**その規範は誰にも届かないまま何も赤くならない**。逆に rules を消して
    `@` 行を残すと解決不能な import になる。どちらの向きも落とす。
    """

    def _imported(self):
        text = ENTRYPOINT.read_text(encoding="utf-8")
        return sorted(set(IMPORT_RE.findall(text)))

    def _present(self):
        return sorted(
            p.relative_to(REPO_ROOT).as_posix() for p in RULES_DIR.glob(RULES_GLOB)
        )

    def _imported_rules(self):
        return sorted(rel for rel in self._imported() if rel.startswith(".claude/rules/"))

    def test_every_rules_file_is_imported_by_the_entrypoint(self):
        missing = sorted(set(self._present()) - set(self._imported_rules()))
        self.assertFalse(
            missing,
            f"`.claude/rules/` にあるが CLAUDE.md の `@` import に無いファイル: {missing}\n"
            "import されないルールファイルは誰にも配送されない。CLAUDE.md の"
            " 「ルールファイル一覧」に `@<相対パス>` 行を追加すること。",
        )

    def test_every_import_resolves_to_an_existing_rules_file(self):
        dangling = sorted(
            rel
            for rel in self._imported_rules()
            if rel.startswith(".claude/rules/") and not (REPO_ROOT / rel).is_file()
        )
        self.assertFalse(
            dangling,
            f"CLAUDE.md が import しているが実在しないルールファイル: {dangling}\n"
            "rules を削除・改名したら CLAUDE.md の `@` 行も同一 PR で更新すること。",
        )

    def test_only_common_guidance_is_imported_outside_the_rules_directory(self):
        external = [
            rel for rel in self._imported() if not rel.startswith(".claude/rules/")
        ]
        self.assertEqual(
            external,
            [COMMON_GUIDANCE],
            "Claude の rules 外 import は、公式 import で直接読む共通 guidance だけを許可する。",
        )

    def test_common_guidance_import_resolves(self):
        self.assertTrue((REPO_ROOT / COMMON_GUIDANCE).is_file())


class TestGovernanceDriftHook(unittest.TestCase):
    def test_common_guidance_edit_is_in_the_observed_set(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            files = {
                "CLAUDE.md": "entrypoint\n",
                ".claude/rules/01-example.md": "rule\n",
                COMMON_GUIDANCE: "changed common\n",
                ".claude/hooks/governance-directives.md": (
                    "<!-- synced-from: CLAUDE.md@000000000000 -->\n"
                ),
            }
            for rel, body in files.items():
                path = root / rel
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(body, encoding="utf-8")
            payload = json.dumps(
                {"tool_input": {"file_path": str(root / COMMON_GUIDANCE)}}
            )
            env = os.environ.copy()
            env["CLAUDE_PROJECT_DIR"] = str(root)
            completed = subprocess.run(
                ["bash", str(REPO_ROOT / ".claude/hooks/check-governance-drift.sh")],
                input=payload,
                text=True,
                capture_output=True,
                env=env,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            output = json.loads(completed.stdout)
            context = output["hookSpecificOutput"]["additionalContext"]
            self.assertIn(f"`{COMMON_GUIDANCE}`（正本集合の一部）", context)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
