**深刻度**: WARNING（現状の実害は限定的だが、stage を design→implementation→verification と進めると、価値＝出力が末端まで落ちない断絶が機械検査を素通りする構造欠陥。オーナー指示「検査されない spec はあってはならない／設計に落ちない nfr も許容できない／全面的にルール充足を見直せ／ノード数の大小を口実にするな」に照らし、価値経路の下流連続性の error 保証は必須）。

**内容**: `config.yml` の接続規則セット（`must_link_to`／`must_be_linked_from`）は、要件→設計まではおおむね上流辺（`must_link_to`）を error で強制するが、**設計→実装→検証の下流連続性（価値＝出力が末端まで落ちること・PR6）を error で強制していない**。以下の型は下流の引き（`must_be_linked_from`）が config に存在せず、「下流に落ちなくても検出されない」＝価値経路の断絶が素通りする（実測 meta.json・605 ノード）。

| 型 | 総数 | 提案 must_be_linked_from | 現状違反 | activate_stage |
|---|---|---|---|---|
| p | 56 | ←[mod]（プロセスは実装モジュールを持つ） | 42 | design |
| mod | 18 | ←[src]（モジュールは実装で実現） | 18 | implementation |
| dm | 6 | ←[src] | 6 | implementation |
| port | 1 | ←[src] | 1 | implementation |
| orc | 2 | ←[src] | 2 | implementation |
| prs | 1 | ←[src] | 1 | implementation |
| prompt | 22 | ←[src]（skill/agent ファイルが実装担体） | 22 | implementation |
| cfg | 14 | ←[src] | 14 | implementation |
| scm | 11 | ←[cfg]（スキーマは設定で具体化・既存 cfg→scm の裏） | 7 | design |
| ds | 3 | ←[prs]（既存 prs→ds の裏） | 2 | design |

さらに **検証・要件段でも下流強制が warning 止まり**で error にできていない：

- `spec←[td]`（テスタブル SPEC はテスト設計で覆われる）が現状 **warning**（config `must_be_linked_from` の `{ node: spec, source: [td], severity: warning }`）。テスタブル（`condition` 有）SPEC = **176 件**が対象で、傘 SPEC 54 件は非テスタブル（RULE-016 exempt）のため除外。→ **leaf（condition 有）限定で error 化**すべき（傘 SPEC は error 化対象から除外）。
- `nfr←[spec]`（NFR は SPEC 導出される）が現状 **warning**（`{ node: nfr, source: [spec], severity: warning }`）。6 NFR は全て `→ nfr-から-spec-導出` SPEC を持つが、error で強制されていないため「設計に落ちない NFR」を機械検出できない。→ **error 化**すべき。

**要オーナー確認の論点**:

1. 上記 `must_be_linked_from` 規則群を config に追加してよいか。src 系（mod/dm/port/orc/prs/prompt/cfg←src）は #160 の SRC 著作後に implementation stage で発火。P←MOD・SCM←CFG・DS←PRS は design stage で即発火可能。
2. 端末ノード `o`（出力・外部 ACTOR へ受け渡す価値の末端）・`verify`（検証成果）は下流義務なしが妥当か（提案：義務なし＝末端なので下流の引きを課さない）。
3. `spec←[td]` を leaf（condition 有）限定で error 化してよいか（傘 SPEC 54 件は非テスタブルにつき除外）。
4. `nfr←[spec]` を error 化してよいか。

**推奨**: 上記規則群を追加し、価値経路を末端（実装・検証）まで error で連続保証する（PR6・オーナー指示の「検査されない spec／設計に落ちない nfr は許容しない」に整合）。ただし規則追加＝機械判定の正本（config.yml）の変更であり、**DD で記録してオーナー確定後に反映**する（本 FND は提案段階・確定ではない）。また `P←MOD` の 42/56 違反は「MOD が P でなく D へ張るケース（型実装 MOD）」を含むため、error 化の前に「全 P が実装モジュールを持つべきか／データ実装 MOD の扱い」を精査し、施行時に過剰発火しないルール設計（例：P のうち実装対象 P に限定する条件付け）を DD で詰める。

**接続規則変更の伝播について（FND-99 パターン・確認済み）**: 本 FND は規則変更の**提案（推奨）段階**であり config.yml をまだ変更しない。よって現時点で out-of-graph 著作資産への同期は不要（差分なし）。ただし**オーナーが規則追加を確定し DD へ昇格・反映する際には**、機械判定の正本（config.yml）だけでなく、該当型（p/mod/dm/port/orc/prs/prompt/cfg/scm/ds/spec/nfr）に対応する著作資産へ必ず同期する：接続マトリクス（`docs/doc-system/03-connection-matrix.md`）・ドキュメント一覧（`docs/doc-system/01-document-items.md`）・各 author（`design-author`／`requirements-author`／`verification-author` とその `.github/agents` ミラー）。伝播漏れは旧ルールでの誤った辺を再生産する（FND-99 パターン）。

**対応状況**: **resolved（2026-07-21）**。DD-9（`接続規則に価値経路の下流連続性を error で機械保証する規則群を追加`＝ `must_be_linked_from` に p←mod／scm←cfg／ds←prs／各種←src を error 追加、`nfr←spec`・`spec←td`（leaf 限定 `applies_when: condition_present`）を warning→error 昇格）＋ DD-10（`SRC シンボル適格性で src⇄設計リンクの誤充足を機械排除・src→mod 拡張`＝`src.kind` × 設計種別のシンボル適格性、src→mod 拡張）で規則を config.yml へ反映し、**#163（Phase B）で `must_be_linked_from` の施行器を実装・merge した**。これにより `must_link_to` に加え `must_be_linked_from` が current_stage gating の下で error として機械施行され、価値経路の下流連続性（PR6）が machine-enforced になった＝本 FND の finding「機械保証していない」は解消。

**論点の決着（DD-9 確定）**:
1. 論点1（規則群の config 追加）＝**全採用**（DD-9 選択肢A）。
2. 論点2（端末ノード `o`／`verify` は下流義務なし）＝**採用**。config.yml に `o`・`verify` を発生源とする追加の `must_be_linked_from` は無い（末端ノードとして下流義務を課さない設計を維持）。
3. 論点3（`spec←td` のテスタブル限定 error 化）＝**採用**。DD-9 で `applies_when: condition_present` により leaf（condition 有）SPEC のみ対象の error に昇格、傘 SPEC（condition 無）は対象外のまま。
4. 論点4（`nfr←spec` の error 化）＝**採用**。DD-9 で warning→error 昇格済み。

**施行結果（別事象・#160/#161 backlog として切り出し済み）**: 実コーパスを `current_stage=design` で施行すると **53 error** が顕在化する（内訳: p←mod 42・scm←cfg 7・ds←prs 2・d←p 2）。これは**規則の欠如ではなく機械保証を得たことで露見したグラフの不完全性**（設計ノードが実装/下流ノードへ落ちきっていない）であり、#160（SRC 著作）／#161（TD/TC/TR 著作）で解消していく backlog である。本 FND（「機械保証の機構が不在」という finding）とはスコープが別の事象であり、本 FND の resolved 化は 53 error の解消を意味しない。

**follow-on（#160/#161 で詰める・精査を失わせない）**: `p←mod` の 42 違反には「全 P が実装モジュールを持つべきか／型実装 MOD（P でなく D へ張るケース）の扱い／実装対象 P への限定条件付け」の精査が未了のまま含まれている（本 FND が error 化前の懸念として指摘していた点・上記「推奨」欄参照）。#160/#161 でグラフを実装/検証まで完成させる際、42 件を素直に MOD 著作で解消するか、規則側を精緻化する（例：実装対象 P に限定する `applies_when`）かの判断が必要。この論点は本 FND の resolved 化により失われない——#160/#161 側で再度検討すること。

**指摘時 ref_version**: 価値経路到達の充足判定 "0.1"（`価値経路到達の充足判定.yaml` v0.1.0 時点。本 FND の対象＝価値経路が末端まで到達することの充足判定を規定する在グラフ SPEC）。config.yml は out-of-graph（版なし・DD-8/FND-104）のため唯一の根拠にしない。
