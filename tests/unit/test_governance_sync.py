"""`governance-directives.md` の synced-from marker が**規範の正本集合**に追従しているかの機械検査。

CLAUDE.md 冒頭の規定：中核規範は毎ターン注入され、その配送用の写しが
`.claude/hooks/governance-directives.md`。**正本は `CLAUDE.md` ＋ `.claude/rules/*.md` ＋
`.ai/guidance/common.md` ＋ `.claude/main-context/*.md`**（写しの項12が要約する主文脈専用の規範）で、
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
    ＋ `<repo_root>/.ai/guidance/common.md` ＋ `<repo_root>/.claude/main-context/*.md`（相対パス昇順）
  - ハッシュ＝各ファイルについて「相対パス(utf-8) + NUL + 生バイト + NUL」を順に連結した
    バイト列の `hashlib.sha256(...).hexdigest()[:12]`
    （相対パスを混ぜるのは、ファイルの分割・改名・並び替えを内容の移動と区別するため）
  - marker＝`<!-- synced-from: CLAUDE.md@<12桁hex> -->`
  （実体＝`.claude/hooks/check-governance-drift.sh` の埋め込み python3。どちらかを変えるときは
  両方を同時に変える。）

併せて、`.claude/rules/*.md` の集合と `CLAUDE.md` の `@` import 行の集合が双方向で一致することも
検査する（F-387-05）。rules は `@` 行の有無にかかわらず自動で読み込まれるが、`@` 行の一覧は
「どのファイルが規約か」を読み手が引く索引なので、rules を追加して `@` 行を足し忘れると索引から
漏れたまま何も赤くならないため。
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
# 正本集合の構成要素（リポジトリルート相対）。check-governance-drift.sh の同名定数と対称に保つ。
ENTRYPOINT = "CLAUDE.md"
RULES_GLOB = ".claude/rules/*.md"
COMMON_GUIDANCE = ".ai/guidance/common.md"
MAIN_CONTEXT_GLOB = ".claude/main-context/*.md"
# 正本集合の相対パスが main-context 由来かを判定する接頭辞（列挙には使わない）。
MAIN_CONTEXT_PREFIX = ".claude/main-context/"
DELIVERY_COPY = REPO_ROOT / ".claude" / "hooks" / "governance-directives.md"
DECISION_PROCESS_RULE = REPO_ROOT / ".claude" / "rules" / "02-decision-process.md"

MARKER_RE = re.compile(r"<!--\s*synced-from:\s*CLAUDE\.md@([0-9a-f]{12})\s*-->")
# CLAUDE.md の import 行（例: `@.claude/rules/01-principles.md`）。
IMPORT_RE = re.compile(r"^@(\S+\.md)\s*$", re.MULTILINE)
OWNER_COMMUNICATION_HEADING = "## オーナーへの報告はチャットが正本"


def _sorted_markdown_relpaths(root, pattern):
    return sorted(p.relative_to(root).as_posix() for p in root.glob(pattern))


def canonical_files(root=REPO_ROOT):
    """正本集合を相対パス昇順で返す（フックの実装と同一の順序規則）。"""
    return (
        [ENTRYPOINT]
        + _sorted_markdown_relpaths(root, RULES_GLOB)
        + [COMMON_GUIDANCE]
        + _sorted_markdown_relpaths(root, MAIN_CONTEXT_GLOB)
    )


def subagent_delivered_files(root=REPO_ROOT):
    """正本集合のうちサブエージェントにも配送されるもの（main-context 以外）。"""
    return [rel for rel in canonical_files(root) if not rel.startswith(MAIN_CONTEXT_PREFIX)]


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

    def test_canonical_set_includes_main_context(self):
        # 写しの項12は main-context の要約なので、正本の変更に追従漏れが出たら検知されなければならない。
        main_context = [rel for rel in canonical_files() if rel.startswith(MAIN_CONTEXT_PREFIX)]
        self.assertTrue(main_context, "`.claude/main-context/*.md` が正本集合に入っていない。")

    def test_common_guidance_and_main_context_bytes_change_the_canonical_hash(self):
        targets = [COMMON_GUIDANCE] + [
            rel for rel in canonical_files() if rel.startswith(MAIN_CONTEXT_PREFIX)
        ]
        for rel_to_change in targets:
            with self.subTest(rel=rel_to_change), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                for rel in canonical_files():
                    path = root / rel
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes((REPO_ROOT / rel).read_bytes())
                before = canonical_hash(root)
                changed = root / rel_to_change
                changed.write_bytes(changed.read_bytes() + b"single-file-change\n")
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
            "CLAUDE.md、.claude/rules/*.md、.ai/guidance/common.md、.claude/main-context/*.md のいずれかを"
            "変更したら、同一 PR で写しの内容を"
            " 突き合わせた上で marker を上記の期待値へ更新する（CLAUDE.md 冒頭の規定）。",
        )


class TestRulesImportsAreComplete(unittest.TestCase):
    """`.claude/rules/*.md` の集合と CLAUDE.md の `@` import 行が双方向一致すること（F-387-05）。

    Claude Code は `.claude/rules/*.md` を `@` 行の有無にかかわらず自動で読み込む（公式仕様・
    Issue #585 で確認。当初の「`@` import が唯一の配線」という前提は誤りだった）。それでも
    `@` 行の一覧は「どのファイルが規約か」を読み手が一覧できる索引なので、rules との乖離を
    残さない。rules を消して `@` 行を残すと解決不能な import になる。どちらの向きも落とす。
    """

    def _imported(self):
        text = (REPO_ROOT / ENTRYPOINT).read_text(encoding="utf-8")
        return sorted(set(IMPORT_RE.findall(text)))

    def _present(self):
        return _sorted_markdown_relpaths(REPO_ROOT, RULES_GLOB)

    def _imported_rules(self):
        return sorted(rel for rel in self._imported() if rel.startswith(".claude/rules/"))

    def test_every_rules_file_is_imported_by_the_entrypoint(self):
        missing = sorted(set(self._present()) - set(self._imported_rules()))
        self.assertFalse(
            missing,
            f"`.claude/rules/` にあるが CLAUDE.md の `@` import に無いファイル: {missing}\n"
            "`@` 行は規約ファイルの索引である（配送は自動読込）。索引から漏れたファイルを残さないよう、"
            "CLAUDE.md の「ルールファイル一覧」に `@<相対パス>` 行を追加すること。",
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
    def test_common_guidance_and_main_context_edits_are_in_the_observed_set(self):
        for edited in (COMMON_GUIDANCE, MAIN_CONTEXT_PREFIX + "01-example.md"):
            with self.subTest(edited=edited):
                context = self._drift_warning_for(edited)
                self.assertIn(f"`{edited}`（正本集合の一部）", context)

    def _drift_warning_for(self, edited):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            files = {
                "CLAUDE.md": "entrypoint\n",
                ".claude/rules/01-example.md": "rule\n",
                COMMON_GUIDANCE: "common\n",
                MAIN_CONTEXT_PREFIX + "01-example.md": "main context\n",
                ".claude/hooks/governance-directives.md": (
                    "<!-- synced-from: CLAUDE.md@000000000000 -->\n"
                ),
            }
            for rel, body in files.items():
                path = root / rel
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(body, encoding="utf-8")
            payload = json.dumps({"tool_input": {"file_path": str(root / edited)}})
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
            return output["hookSpecificOutput"]["additionalContext"]


class TestMainContextOnlyRules(unittest.TestCase):
    """主文脈専用の規範が rules ではなく main-context に置かれること。

    `.claude/rules/` と CLAUDE.md 一式はサブエージェントにも配送されるため、主文脈にしか
    当てはまらない規範は `.claude/main-context/` に置く（配送経路の検査は
    `tests/unit/test_main_context_injection.py`）。
    """

    def test_owner_communication_section_is_not_in_subagent_delivered_files(self):
        for rel in subagent_delivered_files():
            text = (REPO_ROOT / rel).read_text(encoding="utf-8")
            self.assertNotIn(
                OWNER_COMMUNICATION_HEADING,
                text,
                f"{rel} はサブエージェントにも配送される。主文脈専用の節は .claude/main-context/ に置く。",
            )

    def test_main_context_is_not_imported_by_the_entrypoint(self):
        imported = IMPORT_RE.findall((REPO_ROOT / ENTRYPOINT).read_text(encoding="utf-8"))
        self.assertFalse(
            [rel for rel in imported if rel.startswith(MAIN_CONTEXT_PREFIX)],
            "main-context を `@` import するとサブエージェントにも配送される。",
        )


class TestHarnessClassificationTable(unittest.TestCase):
    def test_root_level_generic_harnesses_are_listed_in_the_decision_table(self):
        text = DECISION_PROCESS_RULE.read_text(encoding="utf-8")
        for name in (
            "blocker_gate",
            "pr_merge_gate",
            "time_fixture_lint",
            "issue_start",
            "project_status_sync",
            "branch_source",
            "guidance_sync",
            "defect_metrics",
            "maintainability_lint",
            "codex_hook_trust",
            "codex-hook-trust-check.sh",
        ):
            self.assertIn(
                f"`{name}`",
                text,
                f"{name} の区分を `.claude/rules/02-decision-process.md` の判定表から直接引けるようにすること。",
            )

    def test_decision_table_declares_follow_up_when_new_generic_harnesses_are_added(self):
        text = DECISION_PROCESS_RULE.read_text(encoding="utf-8")
        self.assertIn("新しい汎用ハーネス", text)
        self.assertIn("同一 PR でこの列挙にも追記", text)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
