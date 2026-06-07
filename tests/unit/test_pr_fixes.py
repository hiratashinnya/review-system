"""PR#2 レビュー指摘の修正テスト（A-2）：版DRY(#1)・id衝突(#5)・FB検証(#6/#7)。"""
import unittest
from pathlib import Path

from review_system.prompts.registry import REVIEW_VERSION
from review_system.io import cli
from review_system.persistence.feedback_store import append_feedback


class TestVersionDRY(unittest.TestCase):
    def test_pipeline_uses_registry_version(self):       # #1：版は単一ソース
        from review_system.core import pipeline
        # pipeline は独自ハードコードでなく registry の値を版スタンプに使う
        self.assertEqual(pipeline._PROMPT_TEMPLATE_VERSION, REVIEW_VERSION)


class TestNowPrecision(unittest.TestCase):
    def test_now_has_microseconds(self):                 # #5：秒精度衝突を避ける
        now = cli._now()
        self.assertIn(".", now)                          # microseconds を含む
        self.assertNotEqual(cli._now(), now[:19])         # 秒切り捨てと一致しない


class TestFeedbackStoreValidation(unittest.TestCase):
    def test_missing_keys_raise_valueerror(self):        # #7：不正入力は明確な例外
        import tempfile
        store = Path(tempfile.mkdtemp()) / "fb.jsonl"
        with self.assertRaises(ValueError):
            append_feedback(store, "rid", [{"finding_id": "x"}])   # decision 欠落
        with self.assertRaises(ValueError):
            append_feedback(store, "rid", [{"decision": "approve"}])  # finding_id 欠落


if __name__ == "__main__":
    unittest.main()
