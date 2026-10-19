"""Historical owner words and approval/correction classification (#537 R3)."""

import re
import unittest
from pathlib import Path

from feedback_ledger.store import load_store

ROOT = Path(__file__).resolve().parents[2]
ANNOTATIONS = (
    "（3選択肢提示後）", "（説明後）", "（根拠提示後）", "（本エントリの要否を問うて）",
    "（AI が「追記の根拠は無く、上書きに改める」と回答し、PR 化を提案した後）",
    "（比1.0・連続2窓は）",
)
APPROVALS = (
    "FBK-20260921-qcdはqを制約としcとdを最小化する",
    "FBK-20260924-器はgithub-issue継続で確定する",
    "FBK-20260924-必須施策の実施順を依存関係で確定する",
    "FBK-20260929-進捗スナップショットは現行1枚を上書き更新する",
    "FBK-20261006-harnessの全テストをtests-tool-へ移す",
    "FBK-20261006-harnessテストコードはtests-tool-に置く",
    "FBK-20261006-生存決定の一覧をテーマ別に台帳冒頭へ置く",
)


class MigratedDecisionSemanticsTests(unittest.TestCase):
    def setUp(self):
        self.store = load_store(ROOT)
        self.history = (ROOT / "audit/2026-09-21-pipeline-redesign/history.md").read_text()

    def test_all_48_verbatim_lines_have_source_words_without_editorial_context(self):
        original_lines = re.findall(r"^> ?(.*)$", self.history, re.MULTILINE)
        original_lines.append("項目6は選択肢3がよい")  # 9c18762^ 元§A承認逐語
        for annotation in ANNOTATIONS:
            original_lines = [line.replace(annotation, "") for line in original_lines]
        migrated = [doc for doc in self.store.of("ledger")
                    if doc.data["schema"] == "feedback-ledger/v1.3"]
        self.assertEqual(len(migrated), 48)
        for doc in migrated:
            with self.subTest(entry=doc.data["id"]):
                quote = doc.data["narrative"]["owner_verbatim"]
                for annotation in ANNOTATIONS:
                    self.assertNotIn(annotation, quote)
                for line in quote.splitlines():
                    if line:
                        self.assertIn(line, original_lines)
        backgrounds = "\n".join(doc.data["narrative"]["background"] for doc in migrated)
        for annotation in ANNOTATIONS:
            self.assertIn(annotation, backgrounds)
            self.assertIn(annotation, self.history)

    def test_unchanged_ai_proposals_are_approvals_even_after_a_missing_item_report(self):
        for entry_id in APPROVALS:
            with self.subTest(entry=entry_id):
                self.assertEqual(self.store.by_id("ledger", entry_id).data["divergence"],
                                 "approval")

    def test_owner_added_scope_and_provisional_reservations_are_not_pure_approvals(self):
        for suffix in ("撤退条件aから現行必須施策を除外する", "撤退条件bの閾値は比1と連続2窓とする"):
            data = self.store.by_id("ledger", "FBK-20260924-" + suffix).data
            self.assertEqual(data["divergence"], "narrowing")
        for suffix in ("jevの中間帯は通知しキー無しは止める", "jevの課金を認可し秘密除去を送信条件とする",
                       "jevフック判定器はshadowで試験導入する"):
            data = self.store.by_id("ledger", "FBK-20261006-" + suffix).data
            self.assertEqual(data["divergence"], "reversal")
