**深刻度**: ERROR（発火段 implementation・`current_stage: design` の現在は未発火＝latent）
**対応 Issue**: #256（必須辺検証ルールの見直し・修正 ④ implementation 段 src 系規則の対称化・担体/粒度適格性）

**内容**: `must_link_to` の `src` 行が許容する出辺先は `[mod, dm, port, orc]` の **4型**である一方、`must_be_linked_from` は `mod` / `dm` / `port` / `orc` / `prs` / `prompt` / `cfg` の **7型**が `source: [src]` を要求する。この非対称により、**prs / prompt / cfg のみを被覆する SRC は自身の必須出辺を充足できない**。

- `must_link_to`: `- { node: src, target: [mod, dm, port, orc], activate_stage: implementation, severity: error }`
- `must_be_linked_from`: 上記7型がそれぞれ `- { node: <型>, source: [src], activate_stage: implementation, severity: error }`
- `src_symbol_eligibility`: `mod` / `dm` / `port` / `orc` / `prs` / `prompt` / `cfg` の **7型**を宣言（`must_be_linked_from` 側と一致し、`must_link_to` 側とのみ不一致）

**デッドロックである根拠**: 例えば PROMPT を実現する SRC は、`prompt←src` を満たすために `src→prompt` 辺を持つ必要があるが、`prompt` は `src→` の許容先に無いため `must_link_to` は未充足のまま ERROR になる。回避のために無関係な `src→mod` 等を1本足す逃げ道も、`src_symbol_eligibility` が `mod: [module]` を要求する（PROMPT 担体の SRC は `source.kind` が `module` にならない）ため成立しない。すなわち**規則を変えない限り充足不能**であり、辺の書き足しで解消できる種類の不足ではない。

**影響母数**: prompt 22件・cfg 14件・prs 1件（計37件）が、対応 SRC を著作した時点でこの充足不能に該当し得る。`current_stage` が `implementation` へ進むまで（または #160 の SRC materialize 進行まで）は ERROR として顕在化しない latent 不整合。

**経緯**: `must_be_linked_from` の7型は DD-9（`接続規則に価値経路の下流連続性を-error-で機械保証する規則群を追加`）が「設計ノードは実装(SRC)で実現される」として一括追加した。その後、Q「SRC の必須辺が MOD を対象外とし実装担体の自然な張り先が無い」（decided）を受けて DD-10（`src-シンボル適格性で-src⇄設計リンクの誤充足を機械排除・src→mod-拡張`）が `src→[dm, port, orc]` に `mod` を追加したが、**DD-10 の検討対象は mod/dm/port/orc の4型に閉じており、DD-9 が追加した逆向き7型との整合は取られていない**。片方向のみを拡張した結果として残った取り残しであり、意図的な非対称であることを示す記述は config.yml・DD-9・DD-10 のいずれにも無い。

**選択肢**:
1. `must_link_to` の `src` 行を `target: [mod, dm, port, orc, prs, prompt, cfg]` に拡張し、7型で対称化する。影響＝`must_link_to` 1行の変更のみ。`src_symbol_eligibility` の7型宣言とも一致する。
2. `must_be_linked_from` から `prs` / `prompt` / `cfg` の `source: [src]` 行を削除し、4型に揃える。影響＝DD-9 の決定（prompt/cfg/prs 資産も実装で実現される）の部分撤回になり、37件が実装トレースの機械保証対象から外れる。
3. 両方向の型集合を `src_symbol_eligibility` から導出する単一正本方式へ改める（`must_link_to: src→` と `must_be_linked_from: X←src` を規則行の直書きでなく適格性表から生成／照合する）。影響＝config スキーマと施行器（#163）の改修を伴うが、同種の片方向拡張による再発を構造的に防ぐ。

**推奨**: **1（7型への対称化）を本 sprint の処置とし、3 は別 DD で扱う**。根拠＝(a) `src_symbol_eligibility` が7型を宣言している以上、DD-9/DD-10 が意図した全集合は7型であり、4型に留まる `src→` 側が取り残しと読むのが自然。(b) 2 は DD-9 の決定を巻き戻すため影響母数（37件）が大きく、prompt/cfg 資産の実装トレースを失う。(c) 3 は再発防止として妥当だが config スキーマ・施行器の改修を伴い、latent な本件の解消に必要な最小変更を超える。1 を適用した上で、単一正本化の是非は 3 を論点とする DD で判断する。

**接続規則変更の伝播**: 本 FND の処置（選択肢 1 または 2）は `doc-system-v2/config.yml` の `must_link_to` / `must_be_linked_from` の変更を含むため、処置時に SRC 型を扱う out-of-graph 著作資産（`docs/doc-system/03-connection-matrix.md`・`docs/doc-system/01-document-items.md`）への同期が必要になる。SRC は現行のどの author エージェント（requirements/spec/analysis/design/verification）の担当型にも含まれないため、エージェント定義側の同期対象は現時点で無い。同期の実施は処置側（reconciliation）で行い、実施内容を本ノードに追記する。

**対応状況**: open（`scheduled: sprint-1`・主文脈指定）

**指摘時 ref_version**: must_link_to "0.1"（must_link_to.yaml v0.1.0 時点）
