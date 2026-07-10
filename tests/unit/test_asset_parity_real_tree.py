"""asset_parity — 実リポジトリツリーに対するスモークテスト（クラッシュしないこと・不変条件）。

具体的な MISSING/exempt の件数は今後のポーティング作業で変わりうるため、ここでは
「壊れず走る」「型別モードの判定が効いている」という不変条件だけを固定する（drift の
有無そのものは `--format text/json` を実行して人間/CI が読む）。
"""

import unittest
from pathlib import Path

from asset_parity.inventory import AGENT, MODE_ORCHESTRATOR, MODE_PRINCIPLE, SKILL, scan_canonical
from asset_parity.report import build_report

REPO_ROOT = Path(__file__).resolve().parents[2]


class TestRealTree(unittest.TestCase):
    def test_scan_canonical_finds_known_assets_without_crashing(self):
        assets = scan_canonical(REPO_ROOT)
        names = {(a.kind, a.name): a for a in assets}
        self.assertGreater(len(assets), 20)
        self.assertIn((SKILL, "spec-principles"), names)
        self.assertEqual(names[(SKILL, "spec-principles")].mode, MODE_PRINCIPLE)
        self.assertIn((SKILL, "spec-pipeline"), names)
        self.assertEqual(names[(SKILL, "spec-pipeline")].mode, MODE_ORCHESTRATOR)
        self.assertIn((AGENT, "issue-implementer"), names)

    def test_shared_contract_doc_without_frontmatter_excluded(self):
        assets = scan_canonical(REPO_ROOT)
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


if __name__ == "__main__":
    unittest.main()
