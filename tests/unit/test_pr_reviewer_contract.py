"""契約文の変更検知だけを行い、意味を判定しない。文言変更時は期待文も更新する。"""

import re
import unittest
from pathlib import Path


CONTRACT_PATHS = (".ai/agents/pr-reviewer.md", ".claude/agents/pr-reviewer.md", ".codex/agents/pr-reviewer.toml")
SHARED_RULES = (
    ("差分全文を取得・確認できなかった場合", """差分全文を取得・確認できなかった場合（出力切り詰め、保存ファイルを末尾まで読めない、または全範囲を確認できない場合を含む）は、未確認範囲を明示した `harm: real` / `severity: blocker` / `scope: in` の finding として自己申告し、判定を STOP にする。未確認範囲が PR 差分全体なら locus は `PR#<N>::diff` とし、一部ファイルだけ未確認ならそのファイルのパスを locus とする。未取得部分を推測で評価したり mergeable と判断したりしない。"""),
    ("保存ファイルは実行環境の wrapper が定める読取手段", """保存ファイルは実行環境の wrapper が定める読取手段を使い、最初は約 100 行ずつの範囲を 1 行目から末尾まで重複や欠番なく読み進める。出力に切り詰め表示（`truncated output` 等）が出るか、返却行数が要求行数に満たない場合は、その範囲を半分に分けて読み直す。分割後の各範囲でも、切り詰め表示の有無と要求行数・返却行数を同じ方法で照合する。1 行の範囲でも切り詰め表示が出る場合、または保存後にファイルが短くなった等で 1 行の範囲が空出力になる場合に限り、未確認範囲として自己申告し、判定を STOP にする。利用可能なマニフェストの `lines` がある場合は、全範囲の返却行数合計と照合する。SHA-256 は判定条件にしない。"""),
)
PLATFORM_RULES = {
    ".claude/agents/pr-reviewer.md": ("Claude Code では保存ファイルを Read ツールで", """Claude Code では保存ファイルを Read ツールで読み、Read の出力に示される行番号で各要求範囲が指定行まで返ったことを確認する。終端改行を表示用の空行として別番号にしている場合はその空行を除いた最終データ行番号を利用可能なマニフェストの `lines` と照合する。"""),
    ".codex/agents/pr-reviewer.toml": ("Codex CLI では保存ファイルを `rtk sed -n", """Codex CLI では保存ファイルを `rtk sed -n <開始>,<終了>p <パス>` で範囲ごとに読み、各範囲の実際に返されたデータ行数を数えて要求範囲の行数（終了行 - 開始行 + 1）と一致することを確認する。"""),
}


def normalize(text):
    return re.sub(r"\s+", "", text)


def extract_paragraph(text, start):
    if text.count(start) != 1:
        raise AssertionError(f"expected one rule starting with: {start}")
    marker_at = text.index(start)
    paragraph_start = text.rfind("\n", 0, marker_at) + 1
    paragraph_end = text.find("\n- ", marker_at)
    if paragraph_end < 0:
        paragraph_end = text.find("\n\n", marker_at)
    if paragraph_end < 0:
        paragraph_end = len(text)
    return text[paragraph_start:paragraph_end].strip().removeprefix("- ").strip()


def assert_rule_matches(text, start, expected):
    if normalize(extract_paragraph(text, start)) != normalize(expected):
        raise AssertionError(f"contract wording changed: {start}")


def assert_contract(text, path):
    for start, expected in SHARED_RULES:
        assert_rule_matches(text, start, expected)
    platform_rule = PLATFORM_RULES.get(path)
    if platform_rule:
        assert_rule_matches(text, *platform_rule)


class PrReviewerContractTests(unittest.TestCase):
    def setUp(self):
        self.repository_root = Path(__file__).resolve().parents[2]

    def read_contract(self, path):
        return (self.repository_root / path).read_text(encoding="utf-8")

    def test_contract_wording_matches_expectations_and_shared_rules_match(self):
        shared_clauses = []
        for path in CONTRACT_PATHS:
            text = self.read_contract(path)
            with self.subTest(path=path):
                assert_contract(text, path)
                shared_clauses.append(
                    tuple(normalize(extract_paragraph(text, start)) for start, _ in SHARED_RULES)
                )
        self.assertEqual(shared_clauses, [shared_clauses[0]] * len(CONTRACT_PATHS))

    def test_one_character_wording_change_fails(self):
        path = CONTRACT_PATHS[0]
        text = self.read_contract(path)
        changed = text.replace("`severity: blocker`", "`severity: blockeR`", 1)
        self.assertNotEqual(text, changed)
        with self.assertRaises(AssertionError):
            assert_contract(changed, path)

    def test_whitespace_and_newline_changes_pass(self):
        path = CONTRACT_PATHS[0]
        text = self.read_contract(path)
        for changed in (
            text.replace("未確認範囲を明示した", "未確認範囲を 明示した", 1),
            text.replace("未確認範囲を明示した", "未確認範囲を\n明示した", 1),
        ):
            with self.subTest(changed=changed != text):
                self.assertNotEqual(text, changed)
                assert_contract(changed, path)

    def test_all_pr_diff_commands_require_rtk_prefix(self):
        for path in CONTRACT_PATHS:
            lines = [line for line in self.read_contract(path).splitlines() if "gh pr diff" in line]
            with self.subTest(path=path):
                self.assertTrue(lines)
                for line in lines:
                    self.assertIn("rtk gh pr diff", line)
                    self.assertNotRegex(line, re.compile(r"(?<!rtk )gh pr diff"))


if __name__ == "__main__":
    unittest.main()
