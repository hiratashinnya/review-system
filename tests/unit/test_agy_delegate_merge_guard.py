"""#628 の受入条件を本番 runtime resolver で検査するマージガード。"""

from unittest.mock import patch

from agy_delegate.runtime import verify_runtime
from tests.unit.agy_runtime_cohort_fixture import RuntimeCohortFixture


class RuntimeMergeGuardTests(RuntimeCohortFixture):
    def test_production_runtime_has_no_unverified_stop_reasons(self):
        with patch("subprocess.run", side_effect=self.boundary):
            reasons = verify_runtime(self.request)

        self.assertEqual(
            reasons,
            [],
            "Issue #628: 支持cohortの本番reader/resolver/probe正常契約が停止しました。"
            "検査mock/skip/期待値反転で回避しない。実機5UCは別TRで判定する。"
            f"本番 runtime の未確認停止理由: {reasons}",
        )
