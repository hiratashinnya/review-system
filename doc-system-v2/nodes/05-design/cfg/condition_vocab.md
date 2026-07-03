SPEC・TD の `condition` 属性が取りうる語彙（等価分割クラス）の許容集合。RULE-016 がこの語彙外の値を違反として検出する。
**ファイルパス**: `docs/doc-system/config.yaml`
**主要項目**: `condition_vocab: [normal, boundary, empty, failure, error]`。normal＝ハッピーパス、boundary＝境界値、empty＝空集合/null（boundary と独立）、failure＝仕様違反を正しく検出する sad-path、error＝ツール自身が処理不能な異常入力（fail-close 対象）。
