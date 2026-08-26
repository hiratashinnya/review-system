# spec-pipeline — 設計経緯・移行履歴（rationale・非規範）

> **これは規範ではない。** 正本は `.ai/skills/spec-pipeline/SKILL.md` であり、本文は分担方式と著作 fan-out の背景を保管する。

## ハイブリッド分担の背景

要件・仕様の作業には、オーナー判断や矛盾停止のように対話が必要な段と、親ノードごとに独立して進められる非対話著作がある。DD-22 ①-C で前者を skill の主文脈、後者を `authoring-fanout` とするハイブリッドに整理した。主文脈を薄くしつつ、判断を委譲先へ隠さないためである。

`authoring-fanout` は issue #121 で旧 `spec-authoring-fanout` を requirements/spec を含む複数 author 対応へ汎化した。旧 `/io-event-ledger` skill は 2026-06-11 に廃止し、型別 author エージェントへ著作規約を移管した。

`retry_of` と `error` を再試行に渡す契約は issue #278 で追加した。新しい key を採番せず同じ target の handoff を追跡するためである。

