**前提条件**: 型が PRS（永続化）のノードが存在する（design ステージ到達済み）
**入力/トリガ**: PRS に DS への依存辺がない（`must_link_to: PRS→DS`）
**期待動作**: RULE-006 ERROR を報告する
**例**: PRS-1 が DS への辺を持たない → `ERROR|...|RULE-006|PRS-1|...`
