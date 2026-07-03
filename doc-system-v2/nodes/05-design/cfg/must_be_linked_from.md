各ノード型に課す必須の被依存辺（node ← source 群）ルール群の実インスタンス。あるノードが下流から参照されていること（孤立・終端の穴の検出）を `node`・`source`・`activate_stage`・`severity`・`reason` で列挙する。同一 node の複数行は AND、source が配列なら OR（いずれか1本以上から辺を受ければよい）。
**ファイルパス**: `docs/doc-system/config.yaml`
**主要項目**: `must_be_linked_from:` 配下のルール行群。例＝`{ node: VAL, source: [SR], ... }`・`{ node: SPEC, source: [TD], activate_stage: verification, severity: warning }`。
