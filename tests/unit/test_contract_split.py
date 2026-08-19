"""normative / rationale 分離（Issue #372）の機械検査。

対象＝Issue 運用パイプラインの契約4ファイル。**規範（normative）** は dispatch のたびに
常駐するので行動を決めるものだけを載せ、**経緯（rationale）** は
`.claude/rationale/<name>.md` へ移設する（削除ではなく移設＝PR8「消さない」）。

本テストが固定するのは次の4点。いずれも「分離が静かに崩れる」失敗モードに対応する:

  1. 規範側から rationale へ**1行で辿れる**（リンク切れ・移設し忘れの検知）。
  2. rationale ファイルが**存在し非空**で、非規範であることと移設元を自己申告している
     （規範と誤読されて二重の正本になるのを防ぐ）。
  3. 規範側の常駐字数が分離前を**下回っている**（経緯を規範側へ書き戻す退行の検知）。
  4. `.claude/rationale/` が `asset_parity` の資産として数えられない
     （4ツリー parity に MISSING を生まないという分離の前提の固定）。

**検査範囲外（既知のギャップ・Issue #372 是正ラウンド1／F-372-03）**：`.claude/rationale/README.md`
「3つの規律」の規律2（正本は1箇所・両方に残さない）を機械検査するテストは無い。上記3は
「経緯の**総量**が規範側で増えていないか」の字数上限であり、rationale 側の一節を**逐語コピーで
規範側へ書き戻しても**、字数が分離前の上限を下回っている限りこの budget では検知できない
（=二重正本の検知は現状カバーされていない）。厳密な逐語重複検出は「rationale の正当な参照
（節見出しの引用・リンク文言）」と「経緯の丸ごとコピー」を区別する必要があり誤検知リスクが高いため、
本 PR では追加せず**手動レビュー（PR レビュー時の目視確認）に委ねる**ことをここに明記する。
自動検知を追加する場合は本節を更新すること。

**`CLAUDE.md` ↔ `.claude/hooks/governance-directives.md` の同期検査
（`test_governance_sync.py`）と同型の hash 同期は本件には不要**——あちらは「写し＝コピー」
方式で同じ内容が2箇所にあるため drift を検知する必要があるが、本件は「移設」方式で
実体が1箇所しかないので drift しようがない。

依存仕様（out-of-graph・版なし・補助ナビ）:
  * `.claude/rationale/README.md`（分離の判定軸・3つの規律・4ツリー波及方針）
  * Issue #372（分離の acceptance criteria）
"""

from __future__ import annotations

import pathlib
import unittest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]

# (規範ファイル, rationale ファイル, 常駐字数の上限)
#
# 既定値は「分離前の字数＝base c415c80 で実測」。`NormativeSideStaysLeaner` の docstring が
# 定めるとおり、**分離前を超える正当な規範追加が要るときは根拠付きで更新する**（この上限は
# 経緯の書き戻しを検知するためのもので、規範の正当な追加を妨げる budget ではない）。
#
# Issue #354 PR-4（2026-08-19）で2件を再設定した。追加分はいずれも**経緯ではなく規範**で、
# 内訳は次のとおり（経緯は `.claude/rationale/issue-fixer.md` / `issue-pipeline.md` 側へ書いた）:
#   * `.claude/agents/issue-fixer.md`（14159 → 15200）: ①`isolation: "worktree"` と
#     `ISSUE_FIX_BINDING_V1` marker という**新しい dispatch 前提**の開示（欠けると起動されない
#     ので、書き手が deny の出所を判別するのに要る）、②`adopt-branch` で PR ブランチを取得する
#     **Step 0 の新設**（isolation 化で必須になった手順）、③カルテを CLI 経由でしか触らない規律。
#     `karte_path` の3点検査（絶対パス完全一致・`..`・symlink）は**削除**しており、増分は
#     差し引き後の値。
#   * `.claude/skills/issue-pipeline/SKILL.md`（21663 → 22000）: ②-c の `issue-fixer` dispatch に
#     marker の **field 表**を追加（「どの field に何を書くか」は散文が唯一の伝達手段＝Issue #373 で
#     ②-a について確定した方針の適用）。`karte_path` の受け渡し記述と `git switch <branch>` 手順は
#     **削除**しており、こちらも差し引き後の値。
# 上限値は実測（15098 / 21909）の次の100字境界に置く＝意味のある headroom を与えず、次の追加でも
# 必ずこの comment を更新させる。
CONTRACTS: tuple[tuple[str, str, int], ...] = (
    (".claude/agents/issue-implementer.md",
     ".claude/rationale/issue-implementer.md", 14293),
    (".claude/agents/issue-fixer.md",
     ".claude/rationale/issue-fixer.md", 15200),
    (".claude/agents/pr-reviewer.md",
     ".claude/rationale/pr-reviewer.md", 15051),
    (".claude/skills/issue-pipeline/SKILL.md",
     ".claude/rationale/issue-pipeline.md", 22000),
)


def _read(rel: str) -> str:
    return (REPO_ROOT / rel).read_text(encoding="utf-8")


class NormativeSideLinksToRationale(unittest.TestCase):
    """規律3: 規範側から rationale へ1行で辿れる。"""

    def test_each_normative_file_references_its_rationale(self):
        for normative, rationale, _ in CONTRACTS:
            with self.subTest(normative=normative):
                self.assertIn(
                    rationale, _read(normative),
                    f"{normative} が移設先 {rationale} を参照していない。"
                    " 経緯を移設したら規範側にリンク1行を残すこと（Issue #372）。",
                )


class RationaleSideIsSelfDescribing(unittest.TestCase):
    """規律2: rationale は非空・非規範を自己申告し、移設元を名乗る。"""

    def test_rationale_files_exist_and_are_non_empty(self):
        for _, rationale, _ in CONTRACTS:
            with self.subTest(rationale=rationale):
                path = REPO_ROOT / rationale
                self.assertTrue(path.is_file(), f"{rationale} が存在しない（移設＝削除ではない・PR8）")
                self.assertGreater(len(_read(rationale).strip()), 500,
                                   f"{rationale} が実質空——移設ではなく削除になっている疑い（PR8）")

    def test_rationale_files_declare_non_normative_and_name_their_source(self):
        for normative, rationale, _ in CONTRACTS:
            with self.subTest(rationale=rationale):
                body = _read(rationale)
                self.assertIn(
                    "これは規範ではない", body,
                    f"{rationale} が非規範であることを宣言していない"
                    "（規範と誤読され二重の正本になる）",
                )
                self.assertIn(
                    normative, body,
                    f"{rationale} が移設元 {normative} を名乗っていない",
                )

    def test_rationale_readme_exists(self):
        readme = REPO_ROOT / ".claude" / "rationale" / "README.md"
        self.assertTrue(readme.is_file(), ".claude/rationale/README.md（分離の方針）が無い")


class NormativeSideStaysLeaner(unittest.TestCase):
    """規律: 経緯を規範側へ書き戻す退行を止める。

    上限は「分離前の字数」そのものに置く（きつい budget にしない）。規範の追加そのものは
    正当な変更なので閾値で妨げず、**経緯の書き戻しによる肥大**だけを検知する意図。
    分離前を超える正当な規範追加が要るときは、この期待値を根拠付きで更新する。

    **検査範囲外**：この字数上限は規律2（正本は1箇所）の**代替ではない**。rationale の一節を
    逐語コピーで規範側へ書き戻しても、分離前の字数を下回っている限りここでは検知できない
    （二重正本の検知は未カバー・モジュール docstring 参照・F-372-03）。
    """

    def test_normative_files_are_smaller_than_before_the_split(self):
        for normative, _, before in CONTRACTS:
            with self.subTest(normative=normative):
                after = len(_read(normative))
                self.assertLess(
                    after, before,
                    f"{normative} が分離前（{before}字）以上に膨らんでいる（現在 {after}字）。"
                    " 経緯を規範側へ書き戻していないか確認すること（Issue #372）。",
                )


class RationaleDirIsNotAParityAsset(unittest.TestCase):
    """規律: `.claude/rationale/` は 4ツリー parity の対象外（MISSING を生まない）。

    これは分離の前提そのもの——ここが崩れると `.github`/`.codex`/`.agents` に
    経緯ファイルのミラーを要求され、`asset_parity check` が MISSING で落ちる。
    """

    def test_scan_canonical_ignores_the_rationale_dir(self):
        import sys

        if str(REPO_ROOT) not in sys.path:
            sys.path.insert(0, str(REPO_ROOT))
        from asset_parity.inventory import scan_canonical

        canonical_paths = {a.canonical_path for a in scan_canonical(REPO_ROOT)}
        rationale_dir = REPO_ROOT / ".claude" / "rationale"
        leaked = sorted(str(p) for p in canonical_paths if rationale_dir in p.parents)
        self.assertEqual(
            leaked, [],
            "`.claude/rationale/` の中身が asset_parity の資産として数えられている"
            "——4ツリーにミラーを要求され MISSING になる（Issue #372）",
        )


if __name__ == "__main__":
    unittest.main()
