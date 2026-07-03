**前提条件**: 型が TC のノードが存在する（verification ステージ）
**入力/トリガ**: TC が TR から被依存辺を受けていない（`must_be_linked_from: TC ← [TR]`＝未実行）
**期待動作**: RULE-006 WARNING を報告する（テストは実施されて初めて証跡を残す）
