"""操作区分の正本と配送要約が権限境界を保持する。"""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


class OperationConfirmationPolicyTests(unittest.TestCase):
    def test_issue_creation_skill_preserves_scope_and_unresolved_choices(self):
        text = (ROOT / '.ai/skills/gh-create-issue/SKILL.md').read_text(encoding='utf-8')
        for phrase in ('依頼内の非破壊の通常操作は追加の事前確認なく',
                       '対象と操作が依頼の範囲に一致', 'ユーザーの選択を得る',
                       'Horizon は preview の提示だけを承認とみなさず',
                       '追加の実行確認を求めず'):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

    def test_common_policy_covers_normal_and_restricted_operations(self):
        text = (ROOT / '.ai/guidance/common.md').read_text(encoding='utf-8')
        for phrase in (
            '対象 repo・branch・PR・Issue が一致', '非破壊', '結果を事後報告',
            'non-force push', 'PR 作成', 'Issue 作成', 'CI/check 実行・再実行',
            '依頼範囲外は停止', 'PR merge／auto-merge を実行しない',
            'force push', '個別操作の明示指示', '公開設定・アクセス権変更',
            '本番デプロイ', '第三者へのメール・DM', '機械的な承認ゲート',
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

    def test_delivery_summary_preserves_boundaries(self):
        text = (ROOT / '.claude/hooks/governance-directives.md').read_text(encoding='utf-8')
        section = text.split('12. **オーナーへの報告', 1)[1].split('\n13.', 1)[0]
        for phrase in ('非破壊', '事後報告', '依頼範囲外は停止', '個別の明示指示',
                       'force push', 'remote branch 削除', '履歴改変', '大量削除',
                       '原則事前確認', 'AI の merge は禁止', '機械ゲート'):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, section)
