各ノード型に課す必須の被依存辺（node ← source 群）ルール群の実インスタンス。あるノードが下流から参照されていること（孤立・終端の穴の検出）を `node`・`source`・`activate_stage`・`severity`・`reason`（＋任意の `applies_when`）で列挙する。同一 node の複数行は AND、source が配列なら OR（いずれか1本以上から辺を受ければよい）。DD-9 で価値経路の下流連続性（設計→実装→検証まで落ちること）を error で機械保証する規則群を追加した。
**ファイルパス**: `docs/doc-system/config.yaml`
**主要項目**: `must_be_linked_from:` 配下のルール行群。stage 別の主なルール（config.yml 現行と一致）＝
- requirements: `{ node: val, source: [sr], severity: error }`・`{ node: nfr, source: [spec], severity: error }`（DD-5/DD-9 で warning→error 昇格）等。
- analysis: `{ node: i, source: [p] }`・`{ node: e, source: [p] }`・`{ node: d, source: [p] }`（いずれも error）等。
- design（DD-9 追加・error）: `{ node: p, source: [mod] }`（プロセスは実装モジュールを持つ）・`{ node: scm, source: [cfg] }`（スキーマは設定インスタンスで具体化）・`{ node: ds, source: [prs] }`（データストアは永続化実装で実現）。
- implementation（DD-9 追加・error・シンボル適格性条件付き＝別 DD で `src.kind` × 設計種別のマッチングを機械検証化）: `{ node: mod|dm|port|orc|prs|prompt|cfg, source: [src] }`（設計ノードは実装 SRC で実現される。SRC 著作＝#160 後に発火）。
- verification: `{ node: spec, source: [td], severity: error, applies_when: condition_present }`（DD-9 で warning→error 昇格。テスタブル＝condition 有 leaf-SPEC のみ対象、傘 SPEC＝condition 無は非テスタブルで除外）・`{ node: td, source: [tc] }`・`{ node: tc, source: [tr] }`（warning）等。
**任意フィールド `applies_when`**: 施行器（#163）がノードの属性でルール対象を絞る限定子。現行値＝`condition_present`（`spec←td` に付与）。
