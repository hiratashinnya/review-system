FND ノードの状態（未解消／resolved）に応じて必須辺の向きを逆転させるライフサイクルルールの実インスタンス。`resolved_field` で機械判定フィールド名を指定し、未解消時は forward 辺（FND → 対象）を必須、resolved 時は backward 辺（対象 → FND）を必須かつ forward 辺の不在を期待する。
**ファイルパス**: `docs/doc-system/config.yaml`
**主要項目**: `fnd_lifecycle:` 配下。`resolved_field: resolved`・`unresolved.must_link_to`（target: any・severity error）・`resolved.must_be_linked_from`（source: any・error）・`resolved.must_not_link_to`（target: any・warning）。
