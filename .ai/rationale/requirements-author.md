# requirements-author — 設計経緯・判断記録（非規範）

> これは規範ではない。現行契約は [`.ai/agents/requirements-author.md`](../agents/requirements-author.md) にある。

FR はユーザー価値・必要性の粒度、SPEC はテスタブルな前提・入力・期待動作の粒度へ分ける。これにより「なぜ必要か」と「どう検証するか」を同じ要求ノードへ混ぜず、後段の spec-author が単一アサーションへ分割できる。本文に残すのはこの入力・出力・型別著作契約であり、分割を導入した経緯はここに置く。
