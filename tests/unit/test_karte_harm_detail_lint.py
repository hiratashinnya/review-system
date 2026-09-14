"""``harm_detail`` の内容 lint（Issue #511）の回帰テスト。

対象は ``ingest-review`` の入力パス（:func:`karte.model.parse_review`）と、
誤検出の抑制経路（:mod:`karte.allowlist`）、および **CLI 境界**
（:func:`karte.cli.cmd_ingest_review` の終了コードと台帳の未更新）。

Issue #511 の受け入れ基準に一対一で対応する:
  * 「対応不要の理由」を ``harm_detail`` に書いたレポートが拒否されること。
  * その拒否が ``ingest-review`` の終了コードとして観測でき、台帳が更新されないこと。
  * 正当な実害記述が拒否されないこと。
  * allowlist 経由の例外登録が機能し、登録には理由の記載が必須であること。

`.claude/rules/04-test-data.md`「時刻依存 test data の規律」との関係：本テストは
wall clock を一切読まない（語彙一致は純粋関数）ため対象外。
"""

from __future__ import annotations

import argparse
import contextlib
import io
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from karte import allowlist as karte_allowlist  # noqa: E402
from karte import cli  # noqa: E402
from karte import model  # noqa: E402

ISSUE = 511

# PR #509 / Issue #431 で実際に台帳へ入ってしまった 2 件（Issue #511「実際に発生した混入」）。
REAL_DISPOSITION_LEAK = (
    "依頼したPyright診断は本PRの差分範囲外の既存行における既存パターンで、"
    "新規追加テストによる新規発生ではない"
)
REAL_PROCESS_LEAK = (
    "文書の記述が実装と食い違う（オーナー確認済み・文書側を実装に合わせて訂正する方針で fix-here）"
)
# 上記が round4 で是正されたあとの、正当な実害記述。
VALID_HARM_DETAIL = "required 属性が消え必須入力が素通りする"


def review_report(harm_detail: str, *, title: str = "new") -> str:
    """1 件だけの最小レビューレポートを組み立てる。"""
    return "\n".join(
        [
            "# レビュー結果",
            "",
            f"### {title}",
            "harm: real",
            f"harm_detail: {harm_detail}",
            "severity: major",
            "scope: in",
            "locus: karte/model.py::parse_review",
            "summary: 要約",
            "evidence: karte/model.py:954 を Read した",
            "expected: 期待する観測可能な状態",
            "recheck: 再検証手順",
        ]
    )


class HarmDetailLintTests(unittest.TestCase):
    def test_valid_harm_description_is_accepted(self):
        """正当な実害記述は拒否されない（過検出で書けなくならないこと）。"""
        findings = model.parse_review(review_report(VALID_HARM_DETAIL), ISSUE)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].harm_detail, VALID_HARM_DETAIL)

    def test_disposition_reason_is_rejected(self):
        """「対応不要と判断した理由」を書いたレポートは取り込みごと拒否される。"""
        with self.assertRaises(model.KarteFormatError) as caught:
            model.parse_review(review_report(REAL_DISPOSITION_LEAK), ISSUE)
        message = str(caught.exception)
        self.assertIn("harm_detail", message)
        self.assertIn("差分範囲外", message)
        self.assertIn("新規発生ではない", message)

    def test_process_history_is_rejected(self):
        """プロセス上の経緯（オーナー確認済み・fix-here）も拒否される。"""
        with self.assertRaises(model.KarteFormatError) as caught:
            model.parse_review(review_report(REAL_PROCESS_LEAK), ISSUE)
        message = str(caught.exception)
        self.assertIn("オーナー確認済み", message)
        self.assertIn("fix-here", message)

    def test_error_message_points_at_the_offending_block(self):
        """該当行（lineno）と finding の見出しがエラーに出る（Issue #511 提案挙動）。"""
        with self.assertRaises(model.KarteFormatError) as caught:
            model.parse_review(review_report("対応不要と判断した", title="F-511-01"), ISSUE)
        message = str(caught.exception)
        self.assertIn("F-511-01", message)
        self.assertIn("3 行目", message)

    def test_spacing_and_case_variants_are_detected(self):
        """空白の有無・ASCII の大小文字では逃げられない。"""
        for detail in ("別Issue で直すべき", "別 Issue で直すべき", "FIX-HERE で処置する"):
            with self.subTest(detail=detail):
                with self.assertRaises(model.KarteFormatError):
                    model.parse_review(review_report(detail), ISSUE)

    def test_lint_is_not_applied_to_existing_karte(self):
        """既存カルテの読み取り（``parse``）には掛けない（移行方針・互換性）。"""
        text = "\n".join(
            [
                f"# Karte: issue-{ISSUE}",
                "",
                "## Findings",
                "",
                f"### F-{ISSUE}-01",
                "status: open",
                "harm: real",
                f"harm_detail: {REAL_DISPOSITION_LEAK}",
                "severity: major",
                "scope: in",
                "locus: karte/model.py::parse_review",
                "summary: 要約",
                "evidence: 根拠",
                "expected: 期待",
                "recheck: 再検証",
                "rounds: [1]",
                "resolved_round:",
            ]
        )
        karte = model.parse(text)
        self.assertEqual(karte.findings[0].harm_detail, REAL_DISPOSITION_LEAK)

    def test_other_missing_keys_are_still_reported(self):
        """内容 lint が他の必須キー検証を覆い隠さない。"""
        text = "\n".join(
            [
                "### new",
                "harm_detail: 対応不要と判断した",
                "severity: major",
                "scope: in",
                "summary: 要約",
                "evidence: 根拠",
                "expected: 期待",
                "recheck: 再検証",
            ]
        )
        with self.assertRaises(model.KarteFormatError) as caught:
            model.parse_review(text, ISSUE)
        self.assertIn("'harm' が無い", str(caught.exception))


class HarmDetailAllowlistTests(unittest.TestCase):
    def test_registered_exception_lets_the_report_through(self):
        """理由付きで登録した (issue, term, harm_detail) は取り込みを通す。"""
        detail = "deferred の finding が check の診断網羅要求から外れない"
        entry = karte_allowlist.AllowlistEntry(
            issue=ISSUE,
            term="deferred",
            harm_detail=detail,
            reason=(
                "karte 自身をレビューした指摘で、`deferred` は処置方針の宣言ではなく "
                "karte/model.py の disposition 値そのものを指す仕様用語として現れる。"
            ),
        )
        with mock.patch.object(karte_allowlist, "ALLOWLIST", (entry,)):
            findings = model.parse_review(review_report(detail), ISSUE)
        self.assertEqual(findings[0].harm_detail, detail)

    def test_exception_does_not_leak_to_other_issues(self):
        """別 Issue のレポートには効かない（issue も一致キーの一部）。"""
        detail = "deferred の finding が check の診断網羅要求から外れない"
        entry = karte_allowlist.AllowlistEntry(
            issue=ISSUE,
            term="deferred",
            harm_detail=detail,
            reason="karte 自身のレビューで仕様用語として不可避",
        )
        with mock.patch.object(karte_allowlist, "ALLOWLIST", (entry,)):
            with self.assertRaises(model.KarteFormatError):
                model.parse_review(review_report(detail), ISSUE + 1)

    def test_exception_does_not_leak_to_other_wording(self):
        """文面を書き換えたら再登録が要る（全文一致の粒度）。"""
        detail = "deferred の finding が check の診断網羅要求から外れない"
        entry = karte_allowlist.AllowlistEntry(
            issue=ISSUE,
            term="deferred",
            harm_detail=detail,
            reason="karte 自身のレビューで仕様用語として不可避",
        )
        with mock.patch.object(karte_allowlist, "ALLOWLIST", (entry,)):
            with self.assertRaises(model.KarteFormatError):
                model.parse_review(review_report("deferred なので対応しない"), ISSUE)

    def test_reason_is_mandatory(self):
        """理由のない例外登録は作れない（空・空白のみはどちらも ValueError）。"""
        for reason in ("", "   "):
            with self.subTest(reason=reason):
                with self.assertRaises(ValueError) as caught:
                    karte_allowlist.AllowlistEntry(
                        issue=ISSUE,
                        term="deferred",
                        harm_detail="何らかの実害",
                        reason=reason,
                    )
                self.assertIn("理由", str(caught.exception))

    def test_other_fields_are_validated(self):
        """issue / term / harm_detail の空値も登録できない。"""
        base = dict(issue=ISSUE, term="deferred", harm_detail="何らかの実害", reason="理由")
        for key, bad in (("issue", 0), ("term", " "), ("harm_detail", "")):
            with self.subTest(key=key):
                kwargs = dict(base)
                kwargs[key] = bad
                with self.assertRaises(ValueError):
                    karte_allowlist.AllowlistEntry(**kwargs)

    def test_shipped_allowlist_entries_are_well_formed(self):
        """リポジトリに登録済みの entry はすべて理由を持つ（登録運用の回帰）。"""
        for entry in karte_allowlist.ALLOWLIST:
            with self.subTest(entry=entry):
                self.assertTrue(karte_allowlist.collapse(entry.reason))
                self.assertIn(entry.term, model.HARM_DETAIL_FORBIDDEN_TERMS)
                self.assertTrue(model.find_harm_detail_terms(entry.harm_detail))


class IngestReviewCliTests(unittest.TestCase):
    """CLI 境界での観測を固定する（レビュー finding F-511-04）。

    受入基準は「``python3 -m karte ingest-review`` で拒否されること」であり、実体は
    **終了コード**と**台帳が更新されないこと**の 2 つ。:func:`karte.model.parse_review`
    単体の送出だけを固定していると、書き込み前に必ず parse を通すという現在の
    呼び出し順が将来入れ替わっても（＝拒否したのに台帳へ書かれても）気づけない。
    """

    issue = ISSUE

    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="karte-511-")).resolve()
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        (self.root / "tmp").mkdir()

    def _ingest(self, round_no: int, body: str):
        source = self.root / "tmp" / f"review-{round_no}.md"
        source.write_text(body, encoding="utf-8")
        args = argparse.Namespace(
            issue=str(self.issue),
            repo_root=str(self.root),
            round=str(round_no),
            source=str(source),
        )
        out, errors = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(errors):
            code = cli.cmd_ingest_review(args)
        return code, out.getvalue(), errors.getvalue()

    def _karte_text(self) -> str:
        path = self.root / "tmp" / "_karte" / f"issue-{self.issue}.md"
        return path.read_text(encoding="utf-8") if path.is_file() else ""

    def test_violating_report_fails_the_cli_and_leaves_the_karte_untouched(self):
        code, _, errors = self._ingest(1, review_report(VALID_HARM_DETAIL))
        self.assertEqual(code, cli.EXIT_OK, errors)
        before = self._karte_text()
        self.assertIn(f"F-{ISSUE}-01", before)

        code, _, errors = self._ingest(
            2, review_report(REAL_DISPOSITION_LEAK, title=f"F-{ISSUE}-01")
        )
        self.assertEqual(code, cli.EXIT_ERROR)
        self.assertIn("harm_detail", errors)
        self.assertEqual(self._karte_text(), before)


class ContractSyncTests(unittest.TestCase):
    """契約（`.ai/agents/*.md`）側の是正が残っていることの回帰。"""

    CONTRACT = REPO_ROOT / ".ai" / "agents" / "pr-reviewer.md"
    HANDOFF_ROLES = (
        REPO_ROOT / ".ai" / "agents" / "issue-implementer.md",
        REPO_ROOT / ".ai" / "agents" / "issue-fixer.md",
    )

    def test_contract_no_longer_tells_reviewer_to_write_disposition_into_harm_detail(self):
        text = self.CONTRACT.read_text(encoding="utf-8")
        self.assertNotIn("harm_detail と expected に書いて", text)

    def test_contract_does_not_relocate_the_verdict_into_expected(self):
        """見立ての置き場を expected へ付け替えていない（F-511-02）。"""
        text = self.CONTRACT.read_text(encoding="utf-8")
        self.assertNotIn("見立ては expected", text)
        self.assertIn("見立てはどの欄にも書かない", text)

    def test_contract_limits_harm_detail_to_observable_harm(self):
        text = self.CONTRACT.read_text(encoding="utf-8")
        self.assertIn("harm_detail に書くのは実害だけ", text)
        self.assertIn("karte/allowlist.py", text)

    def test_handoff_roles_carry_the_same_harm_detail_constraint(self):
        """``out_of_scope_findings`` の生産者にも同じ内容制約がある（F-511-03）。"""
        for path in self.HANDOFF_ROLES:
            with self.subTest(role=path.name):
                text = path.read_text(encoding="utf-8")
                self.assertIn("放置したときに何が壊れるかという観測可能な実害だけ", text)
                self.assertIn("処置方針・判断経緯は書かない", text)


if __name__ == "__main__":
    unittest.main()
