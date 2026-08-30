# design-author — 回復手順（非規範）

TERM が見つからない場合は分析層が未著作であるため、design-author は新規 TERM を作らず STOP する。既存 TERM の md/yaml が片方だけ、version が不正、または edges が現行と不一致なら、元ファイルを推測で再構成せず呼び出し元へ返す。

同一 slug の TERM 更新が validator で既存 ID 衝突になった場合は、著作物を削除したり別 slug に変えたりせず、hand-off の `update_slugs` に対象 slug を列挙して再検証する。非宣言 slug やバッチ内重複は更新扱いにせず ROLLBACK とする。
