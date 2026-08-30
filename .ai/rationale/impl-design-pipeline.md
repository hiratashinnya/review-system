# impl-design-pipeline — 設計経緯・却下案（rationale・非規範）

> **これは規範ではない。** 正本は `.ai/skills/impl-design-pipeline/SKILL.md` であり、本文は fan-out と retry 契約の設計背景を保管する。

## 設計層 fan-out の導入

設計物を主文脈の prose のまま残すと、設計層ノードの著作・検証・書込が場当たりになり、複数の親ノードを同じ判断コンテキストで処理することになる。issue #121 以降、設計段の確定物は `authoring-fanout` へ委譲し、依存の薄い Wave1 と Wave2 を分ける形へ整理した。対話的な矛盾停止と DD の暫定決定は主文脈に残すため、fan-out は非対話著作だけを担う。

## `retry_of` を同じ target に結び付ける理由

失敗 target を新しい target として再投入すると、前回の handoff と再試行結果の対応が切れ、同一対象の結果を追跡できない。issue #278 の整理で、再試行には前回の `target_key` と差し戻し理由を渡し、単一対象の再試行は直接 author を呼ぶ契約にした。

