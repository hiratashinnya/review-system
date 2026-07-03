各ノード型に課す必須の依存辺（node → target）ルール群の実インスタンス。requirements 骨格から verification までの全段階を、`node`・`target`・`activate_stage`・`severity`・`reason` の5項目で列挙する。同一 node の複数行は AND（各行が独立検査）、target が配列なら OR（いずれか1本以上）として評価される。
**ファイルパス**: `docs/doc-system/config.yaml`
**主要項目**: `must_link_to:` 配下のルール行群。例＝`{ node: CFG, target: SCM, activate_stage: design, severity: error }`・`{ node: SPEC, target: [FR, NFR, SPEC], ... }`（OR）。
