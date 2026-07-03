`⬡ PREFIX-N` マーカー直後の YAML ブロックが満たすべきフィールドスキーマ。検証ツールのスキーマ検証（P-1-4・RULE-025/026/027/028）が判定する共通必須フィールドの集合・型・各辺の形式を定義する。これにより型不正・必須欠如のノードが後段検査へ持ち込まれない。

**フォーマット**: PyYAML safe_load でパース可能な YAML マップ
**必須フィールド**:
- `id`（文字列・非空。`PREFIX-N[-N...]` 形式・RULE-025）
- `type`（文字列・非空。型ドメイン値＝SCM/CFG/PROMPT 等の prefix に対応・RULE-026）
- `labels`（リスト。空可 `[]`）
- `scheduled`（文字列。空可 `""`・値は config の phases ドメインに属すこと）
- `edges`（リスト。各エントリは `to`（参照先 ID・単数）と `ref_version`（参照先バッジの x.y・RULE-027）を必須とする。`kind`/`status` は持たない＝無名依存辺）
- 型別拡張：SPEC/TD は `condition`、TR は `result`・`log_ref`（RULE-028 で型・欠如を検証）
