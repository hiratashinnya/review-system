# architecture-design — 設計経緯・設計理由（rationale・非規範）

> **これは規範ではない。** 正本は `.ai/skills/architecture-design/SKILL.md` であり、本文は判断の背景だけを保管する。

## ports & adapters を一体で扱う理由

モジュール境界、外部インターフェース、外部連携プロトコル、永続化は、いずれも ports & adapters の境界設計である。これらを同じ依存規則で設計すると、core が外部副作用へ直接依存する分岐や、IF だけ別の責務境界になる不整合を避けられる。

## `sys.path` ハックを禁止する理由

起点ごとに import が変わる構成は、テスト時と出荷時で解決経路がずれ、依存の可視性も損なう。package 構造と絶対 import、`python -m` 起動へ統一することで、実行経路を一つに保ち、差し替え可能な境界を維持する。

