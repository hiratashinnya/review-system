**前提条件**: in-graph ファイルに YAML ブロックが存在し、`id`・`type` は存在する。`edges` リストに1件以上のエントリがある。
**入力/トリガ**: `edges` の任意のエントリに `ref_version` キーが存在しない。
**期待動作**: `edges` エントリに `ref_version` が欠如するとき、`ERROR|{file}:{line}|RULE-027|{id}|edge to {target_id}: ref_version missing` を出力する。
**例**: SPEC-1 ノードの edges に `{to: FR-1}`（ref_version なし）→ `ERROR|doc-system/02-what/03-spec.md:22|RULE-027|SPEC-1|edge to FR-1: ref_version missing`。
