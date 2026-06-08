"""TC-guard-001: PF 境界のガードプロキシ（M1）。アダプタの例外を fail-close に変換。"""
import unittest

from review_system.adapters.fake import FakePlatformAdapter
from review_system.adapters.guard import GuardingPlatform
from review_system.ports.platform import PlatformCapabilities, RawReviewResponse
from review_system.domain.result import Success, Failure, FailureStage


class _RaisingAdapter:
    """壊れた findings.json を読むアダプタ等を模す（review が例外を投げる）。"""
    def capabilities(self) -> PlatformCapabilities:
        return PlatformCapabilities(True, False, False, "m", "raise")

    def review(self, pack, targets, references) -> RawReviewResponse:
        raise ValueError("壊れた PF 出力")


class TestGuardingPlatform(unittest.TestCase):
    def test_exception_becomes_failure(self):            # M1：例外→Failure(EVALUATE)・クラッシュしない
        out = GuardingPlatform(_RaisingAdapter()).review(None, (), ())
        self.assertIsInstance(out, Failure)
        self.assertEqual(out.notice.stage, FailureStage.EVALUATE)
        self.assertTrue(out.notice.next_action.endswith("。"))

    def test_success_passthrough(self):                  # 正常は Success でそのまま通す
        out = GuardingPlatform(FakePlatformAdapter(RawReviewResponse((), ()))).review(None, (), ())
        self.assertIsInstance(out, Success)

    def test_capabilities_delegated(self):               # 能力宣言は内側アダプタへ委譲
        g = GuardingPlatform(FakePlatformAdapter(RawReviewResponse((), ())))
        self.assertEqual(g.capabilities().platform_id, "fake")


if __name__ == "__main__":
    unittest.main()
