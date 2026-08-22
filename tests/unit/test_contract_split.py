"""normative / rationale 分離（Issue #406）の機械検査。

対象＝Issue 運用パイプラインの契約4ファイル。**規範（normative）** は
dispatch のたびに読む現行 `.claude` wrapper、**経緯（rationale）** の正本は
`.ai/rationale/<name>.md` とする。旧 `.claude/rationale/<name>.md` は本文を持たず、
正本への相対ポインタだけを持つ。

本テストが固定するのは次の4点。いずれも「分離が静かに崩れる」失敗モードに対応する:

  1. 現行 `.claude` wrapper から `.ai/rationale` の正本へ辿れる
     （リンク切れ・移設し忘れの検知）。
  2. `.ai/rationale` の本文が**存在し500文字を超え**、非規範であることと移設元を
     自己申告している（規範と誤読されて二重の正本になるのを防ぐ）。
  3. 旧 `.claude/rationale` が対応する `.ai/rationale` を相対参照し、本文を重複保持しない
     （pointer と canonical rationale の責務を混ぜない）。
  4. `.claude/rationale/` が `asset_parity` の資産として数えられない
     （4ツリー parity に MISSING を生まないという分離の前提の固定）。

依存仕様（out-of-graph・版なし・補助ナビ）:
  * `.claude/rationale/README.md`（正本と pointer の方針・4ツリー波及方針）
  * Issue #406（rationale の `.ai` SoT 化と旧 `.claude` pointer の acceptance criteria）
"""

from __future__ import annotations

import os
import pathlib
import re
import unittest
from typing import NamedTuple

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]


class Contract(NamedTuple):
    """Normative wrapper と canonical/pointer rationale の対応。"""

    normative_path: str
    canonical_rationale_path: str
    pointer_path: str


# normative wrapper、rationale の正本、旧ポインタは別々の契約対象として保持する。
CONTRACTS: tuple[Contract, ...] = (
    Contract(
        ".claude/agents/issue-implementer.md",
        ".ai/rationale/issue-implementer.md",
        ".claude/rationale/issue-implementer.md",
    ),
    Contract(
        ".claude/agents/issue-fixer.md",
        ".ai/rationale/issue-fixer.md",
        ".claude/rationale/issue-fixer.md",
    ),
    Contract(
        ".claude/agents/pr-reviewer.md",
        ".ai/rationale/pr-reviewer.md",
        ".claude/rationale/pr-reviewer.md",
    ),
    Contract(
        ".claude/skills/issue-pipeline/SKILL.md",
        ".ai/rationale/issue-pipeline.md",
        ".claude/rationale/issue-pipeline.md",
    ),
)


def _read(rel: str) -> str:
    return (REPO_ROOT / rel).read_text(encoding="utf-8")


def _relative_href(target: pathlib.Path, source_dir: pathlib.Path) -> str:
    """Markdown link に現れる、source_dir から target への相対パスを返す。"""

    return pathlib.PurePosixPath(os.path.relpath(target, source_dir)).as_posix()


class BloomModelTierContract(unittest.TestCase):
    """Codex版を基準にした PF 中立本文と各 PF 写像の分離契約。"""

    COMMON_PATH = ".ai/skills/bloom-model-tier/SKILL.md"
    WRAPPER_PATHS = (
        ".agents/skills/bloom-model-tier/SKILL.md",
        ".claude/skills/bloom-model-tier/SKILL.md",
        ".github/skills/bloom-model-tier/SKILL.md",
    )
    BLOOM_LEVELS = (
        "1 記憶",
        "2 理解",
        "3 応用",
        "4 分析",
        "5 評価",
        "6 創造",
    )
    CODEX_BUDGET_MAPPING = (
        ("最小", "low"),
        ("小", "medium"),
        ("中", "high"),
        ("大", "xhigh"),
        ("最大", "max"),
    )
    CLAUDE_BUDGET_MAPPING = (
        ("最小", "low"),
        ("小", "medium"),
        ("中", "high"),
        ("大", "xhigh"),
        ("最大", "xhigh"),
    )
    EXPECTED_THRESHOLD_CELLS = {
        "1 記憶": (
            "低位モデル層 + 最小の推論予算",
            "低位モデル層 + 大の推論予算",
        ),
        "2 理解": (
            "中位モデル層 + 小の推論予算",
            "中位モデル層 + 大の推論予算",
        ),
        "3 応用": (
            "中位モデル層 + 中の推論予算",
            "中位モデル層 + 大の推論予算",
        ),
        "4 分析": (
            "中位モデル層 + 大の推論予算",
            "中位モデル層 + 大の推論予算",
        ),
        "5 評価": (
            "中位モデル層 + 最大の推論予算",
            "最上位モデル層 + 中の推論予算",
        ),
        "6 創造": (
            "中位モデル層 + 最大の推論予算",
            "最上位モデル層 + 大の推論予算",
        ),
    }

    def test_common_body_keeps_tie_break_and_judgment_examples_specific(self):
        body = _read(self.COMMON_PATH)

        self.assertIn(
            "迷ったら軸2は判断側へ倒し、そのBloom Lvの判断セルを採る",
            body,
        )
        self.assertNotIn(
            "迷ったら軸2は判断ボトルネック側（最上位モデル層）に倒す",
            body,
        )
        self.assertIn(
            "点検しつつ提案＝Evaluate→最上位モデル層 + 中の推論予算",
            body,
        )
        self.assertNotIn("点検しつつ提案＝Evaluate→最上位モデル層）。", body)
        self.assertIn(
            "新規に文章/構造を構成＝Create(6)→判断ボトルネック→最上位モデル層 + 大の推論予算",
            body,
        )
        self.assertNotIn(
            "新規に文章/構造を構成＝Create(6)→判断ボトルネック→最上位モデル層。",
            body,
        )
        self.assertIn(
            "最上位モデル層 + 大の推論予算\n# Bloom Lv6 創造・判断ボトルネック",
            body,
        )

    def test_codex_derived_common_body_keeps_the_full_neutral_contract(self):
        body = _read(self.COMMON_PATH)

        # Codex 正本から移した意味上の契約。単なる Lv 一覧の短縮版へ退行させない。
        for level in self.BLOOM_LEVELS:
            self.assertIn(level, body)
        for marker in (
            "過剰な Lv6",
            "確定したルールや検査結果をテンプレに流し込む",
            "既存資産やコードの整合性",
            "外部 CLI やサブエージェントへ手順通りにディスパッチ",
            "### 軸2：難所の性質",
            "網羅性ボトルネック",
            "判断ボトルネック",
            "## 判定基準（タイブレーク）",
            "## done（点検観点）",
        ):
            self.assertIn(marker, body)

        threshold_table = body[body.index("### 閾値表") : body.index("## 手順")]
        rows = {}
        for line in threshold_table.splitlines():
            if line.startswith("| ") and line.count("|") == 4:
                columns = [column.strip() for column in line.split("|")]
                if columns[1] != "Bloom Lv":
                    rows[columns[1]] = tuple(columns[2:4])

        # 軸2を全Lvに適用し、各セルの層と予算を固定した12セル契約。
        self.assertEqual(set(rows), set(self.EXPECTED_THRESHOLD_CELLS))
        for level, expected_cells in self.EXPECTED_THRESHOLD_CELLS.items():
            row = next(
                line
                for line in threshold_table.splitlines()
                if line.startswith(f"| {level} |")
            )
            self.assertEqual(
                row.count("|"),
                4,
                f"閾値表の {level} 行が網羅性/判断の2セルを持たない。",
            )
            self.assertEqual(rows[level], expected_cells)
            for axis, cell in zip(("網羅性", "判断"), rows[level]):
                self.assertTrue(
                    cell,
                    f"閾値表の {level} の{axis}セルが空である。",
                )

        self.assertNotIn("太字＝", body)
        pf_budget_pattern = re.compile(
            r"(?<![A-Za-z0-9_])(?:low|medium|high|xhigh|max)(?![A-Za-z0-9_])"
        )
        self.assertIsNone(
            pf_budget_pattern.search(body),
            "共通本文に PF 固有の推論予算値を持ち込まない。",
        )
        for forbidden_marker in (
            "Lv4 以上でのみ判定",
            "Lv4 以上なら軸2を判定",
            "軸2（Lv4+のみ）",
        ):
            self.assertNotIn(forbidden_marker, body)
        self.assertNotIn("(該当なし)", body)

        forbidden_pf_tokens = (
            "gpt-5.6",
            "gpt-5.6-luna",
            "gpt-5.6-sol",
            "model_reasoning_effort",
            "haiku",
            "sonnet",
            "opus",
            "effort:",
            "claude-sonnet-5",
            "claude-opus-4-8",
        )
        for token in forbidden_pf_tokens:
            self.assertNotIn(
                token,
                body,
                f"共通本文に PF 固有値 {token!r} を持ち込まない。",
            )

    def test_wrappers_link_common_body_and_keep_pf_mapping_local(self):
        common_href = "../../../.ai/skills/bloom-model-tier/SKILL.md"
        for path in self.WRAPPER_PATHS:
            with self.subTest(wrapper=path):
                self.assertIn(common_href, _read(path))

        codex = _read(".agents/skills/bloom-model-tier/SKILL.md")
        self.assertIn("`gpt-5.6` を固定", codex)
        self.assertIn("`model_reasoning_effort`", codex)
        self.assertIn("session/config", codex)
        self.assertIn("`.codex/agents/*.toml`", codex)
        self.assertNotIn("gpt-5.6-luna", codex)
        self.assertNotIn("gpt-5.6-sol", codex)
        for neutral_budget, codex_budget in self.CODEX_BUDGET_MAPPING:
            self.assertIn(
                f"| {neutral_budget} | `{codex_budget}` |",
                codex,
            )

        claude = _read(".claude/skills/bloom-model-tier/SKILL.md")
        for token in ("haiku", "sonnet", "opus", "effort:"):
            self.assertIn(token, claude)
        for neutral_budget, claude_budget in self.CLAUDE_BUDGET_MAPPING:
            self.assertIn(
                f"| {neutral_budget} | `{claude_budget}` |",
                claude,
            )
        self.assertNotIn("effort:max", claude)
        self.assertNotIn("effort: max", claude)

        copilot = _read(".github/skills/bloom-model-tier/SKILL.md")
        for model_id in ("claude-sonnet-5", "claude-opus-4-8"):
            self.assertIn(model_id, copilot)
        self.assertIn(
            "共通の推論予算は Copilot の agent frontmatter では表現できず、"
            "モデルIDだけを写像する",
            copilot,
        )

    def test_claude_frontmatter_description_keeps_pf_mapping(self):
        claude = _read(".claude/skills/bloom-model-tier/SKILL.md")
        frontmatter_match = re.match(
            r"\A---\n(?P<frontmatter>.*?)\n---\n(?P<body>.*)\Z",
            claude,
            re.DOTALL,
        )
        self.assertIsNotNone(frontmatter_match)
        assert frontmatter_match is not None

        description_match = re.search(
            r"^description:\s*(?P<description>.+)$",
            frontmatter_match.group("frontmatter"),
            re.MULTILINE,
        )
        self.assertIsNotNone(description_match)
        assert description_match is not None
        description = description_match.group("description")

        self.assertIn("model tier", description)
        self.assertIn("reasoning budget", description)
        for model_tier, model_name in (
            ("low-tier", "haiku"),
            ("mid-tier", "sonnet"),
            ("top-tier", "opus"),
        ):
            self.assertRegex(
                description,
                rf"\b{re.escape(model_tier)}\b\s*→\s*{re.escape(model_name)}\b",
            )
        self.assertRegex(
            description,
            r"minimum\s*/\s*small\s*/\s*medium\s*/\s*large\s*/\s*maximum"
            r"\s*→\s*`?effort:\s*low`?\s*/\s*`?medium`?\s*/\s*`?high`?"
            r"\s*/\s*`?xhigh`?\s*/\s*`?xhigh`?",
        )

    def test_individually_managed_list_is_delta_only(self):
        body = _read(".ai/Individually-managed-lists.md")
        self.assertIn("## Bloom の model mapping", body)
        self.assertNotIn("| Bloom Lv |", body)
        self.assertNotIn("### 閾値表", body)
        self.assertNotIn("## 共通本文", body)
        self.assertNotIn("軸2（Lv4+のみ）", body)
        self.assertNotIn("(該当なし)", body)
        self.assertIn("最大の推論予算", body)
        self.assertIn("`effort: xhigh`", body)
        self.assertNotIn("`effort: max`", body)


class NormativeSideLinksToRationale(unittest.TestCase):
    """現行 `.claude` wrapper を入口に canonical rationale へ辿れる。"""

    def test_each_normative_wrapper_reaches_canonical_rationale(self):
        for contract in CONTRACTS:
            with self.subTest(normative=contract.normative_path):
                normative_path = REPO_ROOT / contract.normative_path
                canonical_path = REPO_ROOT / contract.canonical_rationale_path
                wrapper_body = _read(contract.normative_path)
                wrapper_links = re.findall(r"\[[^\]]+\]\(([^)]+)\)", wrapper_body)
                if contract.pointer_path in wrapper_body:
                    route_paths = [(REPO_ROOT / contract.pointer_path).resolve()]
                else:
                    route_paths = [
                        (normative_path.parent / href).resolve()
                        for href in wrapper_links
                        if href.startswith(".") and ".ai/" in href
                    ]
                self.assertEqual(
                    len(route_paths),
                    1,
                    f"{contract.normative_path} から canonical rationale へ辿る経路が"
                    "無い、または複数ある（Issue #406）。",
                )
                route_path = route_paths[0]
                route_body = route_path.read_text(encoding="utf-8")
                if route_path == (REPO_ROOT / contract.pointer_path).resolve():
                    expected_href = _relative_href(canonical_path, route_path.parent)
                    self.assertEqual(
                        re.findall(r"\[[^\]]+\]\(([^)]+)\)", route_body),
                        [expected_href],
                        f"{contract.normative_path} の経由先 {contract.pointer_path} が"
                        f" {contract.canonical_rationale_path} を指していない。",
                    )
                else:
                    self.assertIn(
                        contract.canonical_rationale_path,
                        route_body,
                        f"{contract.normative_path} の参照先 {route_path.relative_to(REPO_ROOT)}"
                        f" から {contract.canonical_rationale_path} を辿れない（Issue #406）。",
                    )
                self.assertTrue(
                    canonical_path.is_file(),
                    f"{contract.canonical_rationale_path} が解決先に存在しない。",
                )


class RationaleSideIsSelfDescribing(unittest.TestCase):
    """canonical `.ai/rationale` は本文を保持し、非規範と移設元を自己申告する。"""

    def test_canonical_rationale_files_exist_and_exceed_500_characters(self):
        for contract in CONTRACTS:
            with self.subTest(rationale=contract.canonical_rationale_path):
                path = REPO_ROOT / contract.canonical_rationale_path
                self.assertTrue(
                    path.is_file(),
                    f"{contract.canonical_rationale_path} が存在しない（移設＝削除ではない・PR8）",
                )
                self.assertGreater(
                    len(_read(contract.canonical_rationale_path).strip()),
                    500,
                    f"{contract.canonical_rationale_path} が500文字以下——canonical rationale"
                    " が実質空になっている疑い（Issue #406）。",
                )

    def test_rationale_files_declare_non_normative_and_name_their_source(self):
        for contract in CONTRACTS:
            with self.subTest(rationale=contract.canonical_rationale_path):
                body = _read(contract.canonical_rationale_path)
                self.assertIn(
                    "これは規範ではない",
                    body,
                    f"{contract.canonical_rationale_path} が非規範であることを宣言していない"
                    "（規範と誤読され二重の正本になる）",
                )
                self.assertIn(
                    contract.normative_path,
                    body,
                    f"{contract.canonical_rationale_path} が移設元 {contract.normative_path} を"
                    "名乗っていない",
                )

    def test_rationale_readme_exists(self):
        readme = REPO_ROOT / ".claude" / "rationale" / "README.md"
        self.assertTrue(readme.is_file(), ".claude/rationale/README.md（分離の方針）が無い")


class RationalePointersAreThin(unittest.TestCase):
    """旧 `.claude/rationale` は canonical rationale への相対ポインタだけを持つ。"""

    def test_each_pointer_references_its_canonical_rationale_without_body(self):
        for contract in CONTRACTS:
            with self.subTest(pointer=contract.pointer_path):
                pointer_path = REPO_ROOT / contract.pointer_path
                canonical_path = REPO_ROOT / contract.canonical_rationale_path
                expected_href = _relative_href(canonical_path, pointer_path.parent)
                pointer_body = _read(contract.pointer_path).strip()
                links = re.findall(r"\[[^\]]+\]\(([^)]+)\)", pointer_body)

                self.assertRegex(
                    pointer_body,
                    r"^\[[^\]]+\]\([^)]+\)$",
                    f"{contract.pointer_path} が単一の Markdown pointer ではない。"
                    " canonical rationale 本文を旧パスに重複保持しないこと（Issue #406）。",
                )
                self.assertEqual(
                    links,
                    [expected_href],
                    f"{contract.pointer_path} が {contract.canonical_rationale_path} を"
                    "相対参照していない。",
                )
                self.assertEqual(
                    (pointer_path.parent / expected_href).resolve(),
                    canonical_path.resolve(),
                    f"{contract.pointer_path} の相対 pointer が canonical rationale を指していない。",
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
            leaked,
            [],
            "`.claude/rationale/` の中身が asset_parity の資産として数えられている"
            "——4ツリーにミラーを要求され MISSING になる（Issue #406）",
        )


if __name__ == "__main__":
    unittest.main()
