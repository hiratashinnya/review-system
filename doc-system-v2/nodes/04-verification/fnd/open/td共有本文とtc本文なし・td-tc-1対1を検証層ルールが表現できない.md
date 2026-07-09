**内容**: 現行 TD/TC は `TD→SPEC`、`TC→TD`、`TD←TC` の必須辺で接続されるが、TD body の共有、TC body なし、TD-TC exactly-one は仕様・schema・validator に表現されていない。DD「識別子単位ノードは1ノード1YAMLを維持し本文は型別ポリシーで省略・共有を許可する」では、1テストプログラムファイル1 TD Markdown body を複数 TD ノードが共有し、TC は本文なしで実テスト識別子のみを持ち、TD-TC は 1:1 と決定した。

**確認した事実**:

- TD テンプレートは1 TD ノードごとの body を想定している。
- TC テンプレートは Markdown body に「実装ファイル」「テスト関数」を書く形であり、機械可読な `test.file` / `test.qualname` ではない。
- `config.yml` は `TD←[TC]` を warning として表すだけで、exactly-one 制約はない。
- `TC→TD` は必須だが、同じ TD を複数 TC が指すことを禁止していない。

**期待される解消**:

1. TD YAML に `body_ref.file` / `body_ref.anchor` を導入する。
2. TC YAML に `test.file` / `test.qualname` / `test.kind` を導入する。
3. TC Markdown body を不要化する。
4. TD-TC 1:1 を SPEC/RULE として追加する。
5. 既存 `TD←TC` / `TC→TD` SPEC を exactly-one 方針に合わせて更新する。
6. TR→TC は現行どおり維持し、TC が実行結果の対象 node であり続けるようにする。

**依存**: body policy の FORMAT/schema 反映後、test-strategy 更新より先に実施する。
