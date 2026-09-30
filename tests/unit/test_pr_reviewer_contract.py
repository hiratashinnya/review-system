"""PR reviewer の差分取得契約を検証する。"""

import re
import unittest
from pathlib import Path


CONTRACT_PATHS = (
    ".ai/agents/pr-reviewer.md",
    ".claude/agents/pr-reviewer.md",
    ".codex/agents/pr-reviewer.toml",
)
POLICY_START = "差分全文を取得・確認できなかった場合"
POLICY_END = "未取得部分を推測で評価したり mergeable と判断したりしない"
POLICY_END_COMPACT = re.sub(r"\s+", "", POLICY_END)
REQUIRED_COMPONENTS = frozenset(
    {
        "applicability",
        "finding_declaration",
        "harm",
        "severity",
        "scope",
        "stop",
        "whole_diff_locus",
        "partial_file_locus",
        "continuous_ranges",
        "requested_range_rows",
        "manifest_total_rows",
        "sha256_not_required",
        "no_guessing",
    }
)
LINE_COUNT_REQUIREMENTS = (
    "要求した各範囲が要求行数まで返ったことを行番号または実際に返されたデータ行数で確認する。",
    "利用可能なマニフェストの `lines` がある場合は全範囲の確認行数合計と照合する。",
    "Read の出力に示される行番号で各要求範囲が指定行まで返ったことを確認する。",
    "終端改行を表示用の空行として別番号にしている場合はその空行を除いた最終データ行番号を利用可能なマニフェストの `lines` と照合する。",
    "各範囲の実際に返されたデータ行数を数えて要求範囲の行数（終了行 - 開始行 + 1）と一致することを確認する。",
    "空出力または行数の不一致は保存後にファイルが短くなった等の欠落として STOP し、",
    "全範囲の返却データ行数合計を利用可能なマニフェストの `lines` と照合する。",
)


def unconfirmed_diff_rule(text):
    if text.count(POLICY_START) != 1:
        raise AssertionError("exactly one unconfirmed-diff rule is required")
    start = text.index(POLICY_START)
    end = text.find(POLICY_END, start)
    if end < 0:
        raise AssertionError("the unconfirmed-diff rule must include the no-guessing clause")
    rule = text[start : end + len(POLICY_END)]
    if "\n\n" in rule:
        raise AssertionError("diff-finding requirements must stay in the same provision")
    return re.sub(r"\s+", "", rule)


def required_diff_finding_components(text):
    rule = unconfirmed_diff_rule(text)
    return {
        "applicability": (
            re.search(r"差分全文を取得・確認できなかった場合(?!以外)", rule) is not None
            and all(
                condition in rule
                for condition in (
                    "出力切り詰め",
                    "保存ファイルを末尾まで読めない",
                    "全範囲を確認できない場合を含む",
                )
            )
        ),
        "finding_declaration": "未確認範囲を明示" in rule and "findingとして自己申告" in rule,
        "harm": "harm:real" in rule,
        "severity": "severity:blocker" in rule,
        "scope": "scope:in" in rule,
        "stop": "判定をSTOPにする" in rule and "判定をSTOPにしない" not in rule,
        "whole_diff_locus": "PR#<N>::diff" in rule and "locusは" in rule,
        "partial_file_locus": "一部ファイルだけ未確認ならそのファイルのパスをlocusとする" in rule,
        "continuous_ranges": (
            "1行目から末尾まで重複や欠番なく連続する範囲で読み" in rule
        ),
        "requested_range_rows": (
            "要求した各範囲が要求行数まで返ったことを行番号または実際に返されたデータ行数で確認する"
            in rule
        ),
        "manifest_total_rows": (
            "利用可能なマニフェストの`lines`がある場合は全範囲の確認行数合計と照合する"
            in rule
        ),
        "sha256_not_required": "SHA-256は判定条件にしない" in rule,
        "no_guessing": POLICY_END_COMPACT in rule,
    }


def assert_required_diff_finding_rule(text):
    found = required_diff_finding_components(text)
    missing = REQUIRED_COMPONENTS - {name for name, present in found.items() if present}
    if missing:
        raise AssertionError(f"missing diff-finding requirement(s): {', '.join(sorted(missing))}")
    return frozenset(name for name, present in found.items() if present)


def omit_line_count_requirements(text):
    for requirement in LINE_COUNT_REQUIREMENTS:
        text = text.replace(requirement, "", 1)
    return text


class PrReviewerContractTests(unittest.TestCase):
    def setUp(self):
        self.repository_root = Path(__file__).resolve().parents[2]

    def read_contract(self, relative_path):
        return (self.repository_root / relative_path).read_text(encoding="utf-8")

    def test_all_pr_diff_commands_require_rtk_prefix(self):
        for relative_path in CONTRACT_PATHS:
            lines = self.read_contract(relative_path).splitlines()
            diff_lines = [line for line in lines if "gh pr diff" in line]
            with self.subTest(path=relative_path):
                self.assertTrue(diff_lines)
                for line in diff_lines:
                    self.assertIn("rtk gh pr diff", line)
                    self.assertNotRegex(line, re.compile(r"(?<!rtk )gh pr diff"))

    def test_all_contracts_check_each_requirement_in_the_same_provision(self):
        found_components = []
        for relative_path in CONTRACT_PATHS:
            with self.subTest(path=relative_path):
                found_components.append(
                    assert_required_diff_finding_rule(self.read_contract(relative_path))
                )
        self.assertEqual(found_components, [REQUIRED_COMPONENTS] * len(CONTRACT_PATHS))

    def test_saved_diff_reading_mechanism_is_platform_specific(self):
        common = self.read_contract(".ai/agents/pr-reviewer.md")
        claude = self.read_contract(".claude/agents/pr-reviewer.md")
        codex = self.read_contract(".codex/agents/pr-reviewer.toml")
        self.assertIn("実行環境の wrapper が定める読取手段", common)
        self.assertNotIn("Codex CLI では", common)
        self.assertNotIn("Read ツールで", common)
        self.assertNotIn("rtk sed -n", common)
        self.assertIn("Claude Code では保存ファイルを Read ツールで", claude)
        self.assertIn("Read の出力に示される行番号", claude)
        self.assertIn(
            "Codex CLI では保存ファイルを `rtk sed -n <開始>,<終了>p <パス>`",
            codex,
        )
        for detail in (
            "要求範囲の行数（終了行 - 開始行 + 1）",
            "空出力または行数の不一致",
            "全範囲の返却データ行数合計",
        ):
            self.assertIn(detail, codex)
        self.assertIn(
            "Bashの先頭コマンドは `gh` または `python3 -m {gitgate,unittest,coverage,dsv2,asset_parity,time_fixture_lint}` に限る。ただし、保存差分の読取に限り `rtk sed -n <開始>,<終了>p <パス>` を例外として許可する",
            codex,
        )
        self.assertIn("対象は `tmp/pr-diffs/pr-<PR番号>-<32桁hex>.diff`", codex)

    def test_contract_rule_allows_line_wrapping_and_synonymous_wording(self):
        for relative_path in CONTRACT_PATHS:
            text = self.read_contract(relative_path)
            mutations = (
                text.replace("場合（出力切り詰め", "場合\n（出力切り詰め", 1),
                text.replace("未確認範囲を明示した", "未確認範囲を明示し", 1),
            )
            for mutated_text in mutations:
                with self.subTest(path=relative_path, mutated=mutated_text != text):
                    self.assertNotEqual(text, mutated_text)
                    assert_required_diff_finding_rule(mutated_text)

    def test_condition_inversion_fails_for_each_contract(self):
        for relative_path in CONTRACT_PATHS:
            text = self.read_contract(relative_path)
            inverted = text.replace(
                "差分全文を取得・確認できなかった場合（",
                "差分全文を取得・確認できなかった場合以外（",
                1,
            )
            with self.subTest(path=relative_path):
                self.assertNotEqual(text, inverted)
                with self.assertRaises(AssertionError):
                    assert_required_diff_finding_rule(inverted)

    def test_stop_negation_fails_for_each_contract(self):
        for relative_path in CONTRACT_PATHS:
            text = self.read_contract(relative_path)
            negated = text.replace("判定を STOP にする。", "判定を STOP にしない。", 1)
            with self.subTest(path=relative_path):
                self.assertNotEqual(text, negated)
                with self.assertRaises(AssertionError):
                    assert_required_diff_finding_rule(negated)

    def test_missing_finding_attribute_fails_for_each_contract(self):
        removals = (
            ("harm", "`harm: real` / "),
            ("severity", "`severity: blocker` / "),
            ("scope", " / `scope: in`"),
        )
        for relative_path in CONTRACT_PATHS:
            text = self.read_contract(relative_path)
            for attribute, fragment in removals:
                mutated = text.replace(fragment, "", 1)
                with self.subTest(path=relative_path, attribute=attribute):
                    self.assertNotEqual(text, mutated)
                    with self.assertRaises(AssertionError):
                        assert_required_diff_finding_rule(mutated)

    def test_missing_line_count_checks_fail_for_each_contract(self):
        for relative_path in CONTRACT_PATHS:
            text = self.read_contract(relative_path)
            mutated = omit_line_count_requirements(text)
            with self.subTest(path=relative_path):
                self.assertNotEqual(text, mutated)
                with self.assertRaises(AssertionError):
                    assert_required_diff_finding_rule(mutated)


if __name__ == "__main__":
    unittest.main()
