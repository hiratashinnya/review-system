"""#628 の受入条件を本番 runtime resolver で検査するマージガード。"""

import json
import tempfile
import unittest
from pathlib import Path

from agy_delegate.permissions import expected_rules
from agy_delegate.runtime import verify_runtime
from agy_delegate.types import Request


class RuntimeMergeGuardTests(unittest.TestCase):
    def test_production_runtime_has_no_unverified_stop_reasons(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            settings = workspace / "synthetic-settings.json"
            settings.write_text(
                json.dumps({"permissions": expected_rules(workspace)}), encoding="utf-8"
            )
            request = Request(
                workspace=workspace,
                settings=settings,
                executable=workspace / "synthetic-agy",
                prompt="merge guard acceptance",
                caller_state="ready",
            )
            reasons = verify_runtime(request)

        unverified_reasons = [
            reason for reason in reasons if reason.partition(":")[0].endswith("_unverified")
        ]
        self.assertEqual(
            unverified_reasons,
            [],
            "Issue #628 が未完了のため意図的に失敗しています。解除条件は #628 の AC。"
            "このテストを skip/削除/期待値反転して緑にしない。"
            f"本番 runtime の未確認停止理由: {unverified_reasons}",
        )
