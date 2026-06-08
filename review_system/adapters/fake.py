"""テスト用 PlatformPort 実装（record/replay）。④ テスト戦略の seam（E）。

非決定（LLM）をこのアダプタ境界で決定化し、core を全関数 unittest 可能にする。
与えた RawReviewResponse をそのまま返す（決定的）。
"""
from __future__ import annotations

from ..ports.platform import (
    PlatformPort, PlatformCapabilities, RawReviewResponse,
)


class FakePlatformAdapter:
    def __init__(self, response: RawReviewResponse, capabilities: PlatformCapabilities | None = None) -> None:
        self._response = response
        self._caps = capabilities or PlatformCapabilities(
            structured_output=True, file_apply=False, tool_execution=False,
            model_id="fake-model", platform_id="fake",
        )

    def capabilities(self) -> PlatformCapabilities:
        return self._caps

    def review(self, pack, targets, references) -> RawReviewResponse:
        return self._response
