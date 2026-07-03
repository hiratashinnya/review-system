**前提条件**: 対象 skill に対応する PROMPT ノードが在グラフに存在する（SPEC-61-1 充足済み）。
**入力/トリガ**: spec-inspector が各 skill PROMPT ノードの edges を走査する。
**期待動作**: 各 skill PROMPT ノードが傘 SPEC-61 への依存辺（`to: SPEC-61`・既存 `must_link_to: PROMPT→SPEC` 規則）を1本持つことを判定する。
**例**: skill `align` の PROMPT ノードの edges に `to: SPEC-61` が存在 → 親辺充足。著作エージェント PROMPT（PROMPT-1〜7）は `to: SPEC-27` を持つため、辺先で本軸と区別される。
