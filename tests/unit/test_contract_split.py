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
