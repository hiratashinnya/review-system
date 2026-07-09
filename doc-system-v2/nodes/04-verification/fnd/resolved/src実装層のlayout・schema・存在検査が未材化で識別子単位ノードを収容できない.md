**内容**: `config.yml` は `must_link_to: SRC→[DM,PORT,ORC]` を保持しているが、implementation stage の `src` layout は未材化であり、SRC ノードを実際に配置・検証する形式がない。既存 SPEC は `@id` realizes 検証を前提にするが、DD「識別子単位ノードは1ノード1YAMLを維持し本文は型別ポリシーで省略・共有を許可する」により、SRC は 1 identifier 1 YAML・Markdown body なし・YAML 側 source 参照が正本となる。

**確認した事実**:

- `doc-system-v2/config.yml` は `implementation stage の src は未材化` とコメントしている。
- `src-の-@id-realizes-検証` 系 SPEC は「ソースに `@id` アノテーションがある」ことを前提にしている。
- 現行 schema には `source.file` / `source.qualname` / `source.kind` 等のコード識別子参照属性がない。

**期待される解消**:

1. `layout` に implementation 層の `src` 配置を追加する。
2. SRC sidecar 用の `source` 属性を定義する。
3. Python AST 等で `source.file + source.qualname` の存在を検査する。
4. `@id` アノテーションを正本にするか補助にするかを明文化する。推奨は YAML を正本、コード内 `@id` は任意補助。
5. SRC→DM/PORT/ORC の必須辺検査を実ノード配置で発火可能にする。

**依存**: bodyless node の FORMAT/schema/validator 追随後に実施する。

**対応内容（2026-07-09・PR #147）**: `06-implementation/src` layout、SRC bodyless 用 `source.file` / `source.qualname` / `source.kind`、SRC 実体参照検査、SRC→DM/PORT/ORC の必須辺検査を PR #147 で反映した。これにより implementation stage の SRC ノードを配置・検証できる状態になったため resolved 化する。

**指摘時 ref_version**: 識別子単位ノードは1ノード1yamlを維持し本文は型別ポリシーで省略・共有を許可する "0.1"（nodes/04-verification/dd/decided/識別子単位ノードは1ノード1yamlを維持し本文は型別ポリシーで省略・共有を許可する.yaml v0.1 時点・provenance）／コード⇔設計の構造比較-段階④・post-mvp "0.2"（nodes/02-what/fr/コード⇔設計の構造比較-段階④・post-mvp.yaml v0.2 時点）／src-の-@id-realizes-検証 "0.3"（nodes/02-what/spec/src-の-@id-realizes-検証.yaml v0.3 時点）
