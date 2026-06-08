"""PF 境界のガード・プロキシ（M1・DD17）。design/04。

アダプタ（翻訳層・例外を投げ得る）を包み、`review()` で**どんな例外も捕捉して
`Failure(EVALUATE)` に変換**する（O-14）。これで core は「例外を投げない PF」
（SafePlatformPort）だけに依存でき、PF 出力を信用しない不変条件（[10]/S3）が
**境界の1箇所**に集約される。能力宣言は内側アダプタへ委譲。
"""
from __future__ import annotations

from ..domain.result import StageOutcome, FailureStage, ok, fail
from ..ports.platform import PlatformPort, PlatformCapabilities, RawReviewResponse


class GuardingPlatform:
    """`PlatformPort`（アダプタ）を包む SafePlatformPort 実装。"""

    def __init__(self, inner: PlatformPort) -> None:
        self._inner = inner

    def capabilities(self) -> PlatformCapabilities:
        return self._inner.capabilities()

    def review(self, pack, targets, references) -> StageOutcome[RawReviewResponse]:
        try:
            return ok(self._inner.review(pack, targets, references))
        except Exception as e:                       # PF/アダプタの一切の失敗を fail-close 化
            return fail(FailureStage.EVALUATE, f"PF 評価に失敗: {e}", None,
                        "PF 応答が不正/到達不能です。findings.json か PF 接続を確認してください。")
