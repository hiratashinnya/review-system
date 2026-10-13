"""asset_parity — 実リポジトリツリーに対するスモークテスト（クラッシュしないこと・不変条件）。

具体的な MISSING/exempt の件数は今後のポーティング作業で変わりうるため、ここでは
「壊れず走る」「型別モードの判定が効いている」という不変条件だけを固定する（drift の
有無そのものは `--format text/json` を実行して人間/CI が読む）。
"""

import unittest
from pathlib import Path

from asset_parity.inlining import is_inlined_into_copilot_instructions
from asset_parity.inventory import AGENT, MODE_ORCHESTRATOR, MODE_PRINCIPLE, SKILL, scan_parity_seeds
from asset_parity.report import STATUS_EXEMPT, STATUS_PRESENT, build_report

REPO_ROOT = Path(__file__).resolve().parents[2]


class TestRealTree(unittest.TestCase):
    def test_scan_parity_seeds_finds_known_assets_without_crashing(self):
        assets = scan_parity_seeds(REPO_ROOT)
        names = {(a.kind, a.name): a for a in assets}
        self.assertGreater(len(assets), 20)
        self.assertIn((SKILL, "spec-principles"), names)
        self.assertEqual(names[(SKILL, "spec-principles")].mode, MODE_PRINCIPLE)
        self.assertIn((SKILL, "spec-pipeline"), names)
        self.assertEqual(names[(SKILL, "spec-pipeline")].mode, MODE_ORCHESTRATOR)
        self.assertIn((AGENT, "issue-implementer"), names)

    def test_shared_contract_doc_without_frontmatter_excluded(self):
        assets = scan_parity_seeds(REPO_ROOT)
        names = {(a.kind, a.name) for a in assets}
        self.assertNotIn((AGENT, "doc-system-v2-authoring"), names)

    def test_build_report_runs_end_to_end(self):
        report = build_report(REPO_ROOT)
        self.assertGreater(len(report.rows), 20)
        # documented exemptions from tailoring-registry.md must not show up as MISSING
        by_name = {(row.asset.kind, row.asset.name): row for row in report.rows}
        from asset_parity.report import STATUS_MISSING
        from asset_parity.trees import GITHUB
        self.assertNotEqual(by_name[(SKILL, "issue-pipeline")].cells[GITHUB].status, STATUS_MISSING)
        self.assertNotEqual(by_name[(AGENT, "issue-implementer")].cells[GITHUB].status, STATUS_MISSING)

    def test_every_principle_skill_github_cell_matches_actual_inlining(self):
        from asset_parity.trees import GITHUB
        report = build_report(REPO_ROOT)
        principles = [r for r in report.rows if r.asset.mode == MODE_PRINCIPLE]
        self.assertTrue(principles)
        for row in principles:
            cell = row.cells[GITHUB]
            reason = cell.reason or ""
            if is_inlined_into_copilot_instructions(row.asset, REPO_ROOT):
                self.assertEqual(cell.status, STATUS_EXEMPT, row.asset.name)
                self.assertIn("inlined", reason, row.asset.name)
            else:
                # Not inlined: a discrete Copilot file (present) or a documented exemption.
                # An unregistered gap is MISSING, which must fail here.
                self.assertNotIn("inlined per", reason, row.asset.name)
                self.assertIn(cell.status, {STATUS_PRESENT, STATUS_EXEMPT}, row.asset.name)
                if cell.status == STATUS_EXEMPT:
                    self.assertTrue(reason, row.asset.name)

    def test_spec_principles_is_inlined_into_copilot_instructions(self):
        assets = {a.name: a for a in scan_parity_seeds(REPO_ROOT) if a.kind == SKILL}
        self.assertTrue(is_inlined_into_copilot_instructions(assets["spec-principles"], REPO_ROOT))


if __name__ == "__main__":
    unittest.main()
