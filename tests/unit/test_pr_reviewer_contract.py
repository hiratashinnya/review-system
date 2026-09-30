"""PR reviewer の差分取得契約を検証する。"""

import re
import unittest
from pathlib import Path


CONTRACT_PATHS = (
    ".ai/agents/pr-reviewer.md",
    ".claude/agents/pr-reviewer.md",
    ".codex/agents/pr-reviewer.toml",
)
DIFF_FINDING_RULE = (
    "差分全文を取得・確認できなかった場合（出力切り詰め、保存ファイルを末尾まで読めない、または全範囲を確認できない場合を含む）は、"
    "未確認範囲を明示した `harm: real` / `severity: blocker` / `scope: in` の finding として自己申告し、判定を STOP にする。"
    "未確認範囲が PR 差分全体なら locus は `PR#<N>::diff` とし、一部ファイルだけ未確認ならそのファイルのパスを locus とする。"
    "保存ファイルは 1 行目から末尾まで重複や欠番なく連続する範囲で読み、利用可能なマニフェストの `lines` と照合し、"
    "終端改行を表示用の空行として別番号にしている場合はその空行を除いた最終データ行番号が `lines` と一致することを確認する。"
    "SHA-256 は判定条件にしない。"
)
READ_MECHANISM_PREFIXES = (
    "保存ファイルは実行環境の wrapper が定める読取手段で ",
    "Claude Code では保存ファイルを Read ツールで ",
    "Codex CLI では保存ファイルを `rtk sed -n <開始>,<終了>p <パス>` で範囲ごとに読み、",
)


def required_diff_finding_rules(text):
    for prefix in READ_MECHANISM_PREFIXES:
        text = text.replace(prefix, "保存ファイルは ", 1)
    normalized_text = re.sub(r"\s+", "", text)
    normalized_rule = re.sub(r"\s+", "", DIFF_FINDING_RULE)
    return [normalized_rule] * normalized_text.count(normalized_rule)


def assert_required_diff_finding_rule(text):
    rules = required_diff_finding_rules(text)
    if len(rules) != 1:
        raise AssertionError("exactly one complete diff finding rule is required")
    return rules[0]


class PrReviewerContractTests(unittest.TestCase):
    def test_all_pr_diff_commands_require_rtk_prefix(self):
        repository_root = Path(__file__).resolve().parents[2]
        for relative_path in CONTRACT_PATHS:
            contract_path = repository_root / relative_path
            lines = contract_path.read_text(encoding="utf-8").splitlines()
            diff_lines = [line for line in lines if "gh pr diff" in line]
            with self.subTest(path=relative_path):
                self.assertTrue(diff_lines)
                for line in diff_lines:
                    self.assertIn("rtk gh pr diff", line)
                    self.assertNotRegex(line, re.compile(r"(?<!rtk )gh pr diff"))


    def test_all_contracts_bind_unconfirmed_diff_to_finding_locus_and_read_check(self):
        repository_root = Path(__file__).resolve().parents[2]
        matched_rules = []
        for relative_path in CONTRACT_PATHS:
            text = (repository_root / relative_path).read_text(encoding="utf-8")
            with self.subTest(path=relative_path):
                matched_rules.append(assert_required_diff_finding_rule(text))
        self.assertEqual(len(matched_rules), len(CONTRACT_PATHS))
        self.assertEqual(len(set(matched_rules)), 1)

    def test_saved_diff_reading_mechanism_is_platform_specific(self):
        repository_root = Path(__file__).resolve().parents[2]
        common = (repository_root / ".ai/agents/pr-reviewer.md").read_text(encoding="utf-8")
        claude = (repository_root / ".claude/agents/pr-reviewer.md").read_text(encoding="utf-8")
        codex = (repository_root / ".codex/agents/pr-reviewer.toml").read_text(encoding="utf-8")
        self.assertIn("実行環境の wrapper が定める読取手段", common)
        self.assertNotIn("Read ツールで", common)
        self.assertNotIn("rtk sed -n", common)
        self.assertIn("Claude Code では保存ファイルを Read ツールで", claude)
        self.assertIn(
            "Codex CLI では保存ファイルを `rtk sed -n <開始>,<終了>p <パス>` で範囲ごとに読み",
            codex,
        )
        self.assertIn(
            "Bashの先頭コマンドは `gh` または `python3 -m {gitgate,unittest,coverage,dsv2,asset_parity,time_fixture_lint}` に限る。ただし、保存差分の読取に限り `rtk sed -n <開始>,<終了>p <パス>` を例外として許可する",
            codex,
        )
        self.assertIn(
            "対象は `tmp/pr-diffs/pr-<PR番号>-<32桁hex>.diff`",
            codex,
        )

    def test_contract_rule_allows_markdown_line_wrapping(self):
        repository_root = Path(__file__).resolve().parents[2]
        for relative_path in CONTRACT_PATHS:
            text = (repository_root / relative_path).read_text(encoding="utf-8")
            wrapped_text = text.replace("場合（出力切り詰め", "場合\n（出力切り詰め", 1)
            with self.subTest(path=relative_path):
                self.assertNotEqual(text, wrapped_text)
                assert_required_diff_finding_rule(wrapped_text)

    def test_condition_inversion_fails_for_each_contract(self):
        repository_root = Path(__file__).resolve().parents[2]
        for relative_path in CONTRACT_PATHS:
            text = (repository_root / relative_path).read_text(encoding="utf-8")
            inverted_text = text.replace(
                "差分全文を取得・確認できなかった場合（",
                "差分全文を取得・確認できなかった場合以外（",
                1,
            )
            with self.subTest(path=relative_path):
                self.assertNotEqual(text, inverted_text)
                with self.assertRaises(AssertionError):
                    assert_required_diff_finding_rule(inverted_text)

    def test_stop_negation_fails_for_each_contract(self):
        repository_root = Path(__file__).resolve().parents[2]
        for relative_path in CONTRACT_PATHS:
            text = (repository_root / relative_path).read_text(encoding="utf-8")
            negated_text = text.replace("判定を STOP にする。", "判定を STOP にしない。", 1)
            with self.subTest(path=relative_path):
                self.assertNotEqual(text, negated_text)
                with self.assertRaises(AssertionError):
                    assert_required_diff_finding_rule(negated_text)


if __name__ == "__main__":
    unittest.main()
