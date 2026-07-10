"""asset_parity.report — presence/absence マトリクス構築・orphan 検出・exit 判定の契約。"""

import unittest

from asset_parity.inventory import AGENT, SKILL
from asset_parity.report import (
    STATUS_EXEMPT,
    STATUS_MISSING,
    STATUS_NA,
    STATUS_PRESENT,
    build_report,
    render_json,
    render_text,
    to_jsonable,
)
from asset_parity.trees import AGENTS_DIR, CODEX, GITHUB

from tests.unit.asset_parity_fixtures import make_tree


def _fake_exempt(name, kind, tree):
    if (name, kind, tree) in {("exempt-skill", SKILL, GITHUB), ("exempt-agent", AGENT, GITHUB)}:
        return "test-fixture documented exemption"
    return None


class TestBuildReport(unittest.TestCase):
    def setUp(self):
        self.root = make_tree(self)
        self.report = build_report(
            self.root,
            commit_epoch_fn=lambda p, r: None,  # git 履歴なし tmp ツリー → staleness は常に非フラグ
            is_exempt_fn=_fake_exempt,
        )
        self.by_name = {(row.asset.kind, row.asset.name): row for row in self.report.rows}

    def test_plain_skill_present_everywhere_applicable(self):
        row = self.by_name[(SKILL, "plain-skill")]
        self.assertEqual(row.cells[GITHUB].status, STATUS_PRESENT)
        self.assertEqual(row.cells[AGENTS_DIR].status, STATUS_PRESENT)
        self.assertEqual(row.cells[CODEX].status, STATUS_NA)  # skill はそもそも codex 非適用

    def test_orchestrator_skill_present_via_prompt_path(self):
        row = self.by_name[(SKILL, "orchestrator-skill")]
        self.assertEqual(row.cells[GITHUB].status, STATUS_PRESENT)
        self.assertTrue(str(row.cells[GITHUB].path).endswith(".prompt.md"))

    def test_principle_skill_github_is_structural_exempt(self):
        row = self.by_name[(SKILL, "principle-skill")]
        self.assertEqual(row.cells[GITHUB].status, STATUS_EXEMPT)
        self.assertIn("inlined", row.cells[GITHUB].reason)
        # agents_dir 側は普通に present（構造的例外は github だけに効く）
        self.assertEqual(row.cells[AGENTS_DIR].status, STATUS_PRESENT)

    def test_missing_everywhere_flagged_missing_not_exempt(self):
        row = self.by_name[(SKILL, "missing-everywhere-skill")]
        self.assertEqual(row.cells[GITHUB].status, STATUS_MISSING)
        self.assertEqual(row.cells[AGENTS_DIR].status, STATUS_MISSING)

    def test_documented_exemption_reported_as_exempt_not_missing(self):
        row = self.by_name[(SKILL, "exempt-skill")]
        self.assertEqual(row.cells[GITHUB].status, STATUS_EXEMPT)
        self.assertEqual(row.cells[GITHUB].reason, "test-fixture documented exemption")
        # agents_dir 側は present（exempt はツリー単位で効く）
        self.assertEqual(row.cells[AGENTS_DIR].status, STATUS_PRESENT)

        agent_row = self.by_name[(AGENT, "exempt-agent")]
        self.assertEqual(agent_row.cells[GITHUB].status, STATUS_EXEMPT)
        self.assertEqual(agent_row.cells[CODEX].status, STATUS_PRESENT)

    def test_missing_agent_flagged_missing(self):
        row = self.by_name[(AGENT, "missing-agent")]
        self.assertEqual(row.cells[GITHUB].status, STATUS_MISSING)
        self.assertEqual(row.cells[CODEX].status, STATUS_MISSING)

    def test_no_frontmatter_agent_excluded_from_rows(self):
        self.assertNotIn((AGENT, "no-frontmatter"), self.by_name)

    def test_missing_count_matches_expected(self):
        # missing-everywhere-skill: github + agents_dir = 2 / missing-agent: github + codex = 2
        self.assertEqual(self.report.missing_count, 4)

    def test_render_text_contains_expected_rows_and_summary(self):
        text = render_text(self.report)
        self.assertIn("plain-skill", text)
        self.assertIn("MISSING", text)
        self.assertIn("assets checked", text)

    def test_orphan_in_mirror_detected(self):
        codex_orphans = self.report.orphans.get(CODEX, [])
        self.assertIn("codex-only-agent (agent)", codex_orphans)
        # 正本に実在する asset は orphan として出ない
        self.assertNotIn("plain-agent (agent)", codex_orphans)

    def test_render_json_round_trips(self):
        payload = to_jsonable(self.report)
        self.assertEqual(payload["summary"]["missing_count"], 4)
        names = {a["name"] for a in payload["assets"]}
        self.assertIn("plain-skill", names)
        json_text = render_json(self.report)
        self.assertIn('"missing_count": 4', json_text)


if __name__ == "__main__":
    unittest.main()
