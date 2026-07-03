# doc-system v1 → v2 移行レポート（Sub-B #71）

- 移行ノード数: **585**
- edge 総数（合成込み）: **1008**（うち合成した親 edge: **67**）
- dangling edge（未解決 to）: **0**
- 傘 SPEC（condition:normal）で condition を落としたノード: **31**
- 再生成前に除去した既存ノードファイル数: **6**

> **Sub-A サンプルノードの扱い**: 移行前の `nodes/` には Sub-A の**サンプルノード**（FORMAT.md §検証 が「サンプル」と明記）3 件が置かれていた。うち 2 件（傘 SPEC＝SPEC-62／子 SPEC＝SPEC-62-2）は v1 実ノードに対応するため移行で**同一 slug に再生成**される。残る 1 件（FND『サイドカーに status を持たせず path 導出とする設計判断の要確認』＝v2 自体の設計に関するSub-A デモ用 finding・v1 コーパスに存在しない）は、本移行が生成する v1 由来 585 ノードには含まれず、厳密 585 ノード化のため除去した（内容は git 履歴・PR #77 に保全）。v2 verification 層のネイティブ finding として残すべきかはオーナー判断。

## 型別件数（v2 生成）
| type | 件数 |
|------|------|
| actor | 2 |
| cfg | 14 |
| d | 21 |
| dd | 22 |
| dm | 6 |
| ds | 3 |
| e | 2 |
| fnd | 112 |
| fr | 17 |
| i | 5 |
| mod | 18 |
| nfr | 6 |
| o | 6 |
| orc | 2 |
| p | 56 |
| pend | 2 |
| port | 1 |
| prompt | 20 |
| prs | 1 |
| q | 6 |
| scm | 10 |
| spec | 228 |
| sr | 8 |
| term | 6 |
| val | 6 |
| verify | 5 |
| **合計** | **585** |

## status 分布（path 導出）
- dd/decided: 22
- fnd/open: 11
- fnd/resolved: 101
- pend/deferred: 1
- pend/resolved: 1
- q/closed: 5
- q/open: 1

## グラフ照会（生成物に対する dsv2 drift / orphans）
- ドリフト辺（RULE-004）: **45** 件（v1 由来の凍結記録・ref_version スナップショットの自然発火）。
- うち suppress:[RULE-004] により**免除**された辺: **24** 件（VERIFY 5 ノード＝過去の検証事実スナップショット・DD-2）。免除辺は上記 45 件に含まれない。
- 完全孤立ノード（in/out 辺 0・RULE-005 相当）: **9** 件。（v1 でも孤立していた DD/FND 等・移行で新規孤立は発生していない）。

<details><summary>完全孤立ノード一覧</summary>

- `config-駆動の-禁止接続-辺残留-検出に専用-rule-030-を新設-欠如-rule-006-と残存-rule-030-を責務`（04-verification/dd）
- `filesystemport-の抽象化粒度`（04-verification/dd）
- `resolved-の-boolean-型検証-spec-60-3-に専用-rule-031-を新設-共通必須型-rule-028-と型別任意型-rule-0`（04-verification/dd）
- `検証戦略の段階別トリガを-§1-フロー図-l13-23-の単一トリガに統一-bump-非依存の辺残留検`（04-verification/dd）
- `設計接続規則の決定-fnd-96・dd-15-が-out-of-graph-著作資産に未伝播`（04-verification/fnd）
- `pr-#22-説明文が実変更と大きく乖離-fnd-29-再発`（04-verification/fnd）
- `tmp-草稿のコミット運用が継続されていない`（04-verification/fnd）
- `本文-resolved／機械-unresolved-の状態ドリフト-19-件-resolved-true-フラグ欠落・forward-辺残置`（04-verification/fnd）
- `検証戦略-05-verification.md-の段階別トリガ宣言がフロー図の単一トリガモデルと不整合-バッ`（04-verification/fnd）

</details>

## slug 衝突の解消
| 解消後 slug | 元 id | サイドカー title |
|------|------|------|
| `config.yaml-ds` | DS-2 | config.yaml（DS） |
| `config.yaml-i` | I-5 | config.yaml（I） |
| `スキーマ検証-p-1-4` | P-1-4 | スキーマ検証（P-1-4） |
| `スキーマ検証-p-5-2` | P-5-2 | スキーマ検証（P-5-2） |

## 旧 id → slug 対応表
| 旧 id | slug | type |
|------|------|------|
| ACTOR-1 | `仕様著者` | actor |
| ACTOR-2 | `レビュアー` | actor |
| CFG-1 | `config.yaml-設定インスタンス` | cfg |
| CFG-1-1 | `current_phase` | cfg |
| CFG-1-10 | `condition_vocab` | cfg |
| CFG-1-11 | `coverage_rules` | cfg |
| CFG-1-12 | `always_error` | cfg |
| CFG-1-13 | `trace_scope` | cfg |
| CFG-1-2 | `current_stage` | cfg |
| CFG-1-3 | `phases` | cfg |
| CFG-1-4 | `stages` | cfg |
| CFG-1-5 | `must_link_to` | cfg |
| CFG-1-6 | `must_be_linked_from` | cfg |
| CFG-1-7 | `fnd_lifecycle` | cfg |
| CFG-1-8 | `decision_spine` | cfg |
| CFG-1-9 | `rule_activation` | cfg |
| D-1 | `in-graph-ファイル集合` | d |
| D-10 | `必須接続規則` | d |
| D-11 | `決定スパイン規則` | d |
| D-12 | `always-error-規則` | d |
| D-13 | `condition-語彙・網羅規則` | d |
| D-14 | `ルール発火ステージ表` | d |
| D-15 | `ハブ閾値設定` | d |
| D-16 | `走査スコープ設定` | d |
| D-17 | `接続検査ビュー` | d |
| D-18 | `属性検査ビュー` | d |
| D-19 | `決定辺ビュー` | d |
| D-20 | `分析層トポロジビュー` | d |
| D-21 | `仕様カバレッジビュー` | d |
| D-22 | `グラフトポロジビュー` | d |
| D-3 | `設定オブジェクト` | d |
| D-4 | `構造化ノードセット` | d |
| D-5 | `パース段違反リスト` | d |
| D-6 | `rule-違反リスト` | d |
| D-7 | `カバレッジ計測結果` | d |
| D-8 | `ノード草案-tmp-草案` | d |
| D-9 | `フェーズ・ステージ状態` | d |
| DD-1 | `sr-4-を-sr-2-の重複として削除し被依存を-sr-2-へ再配線` | dd |
| DD-10 | `spec-47-nfr-1-の-frontmatter-参照を-dd-8-準拠に修正` | dd |
| DD-11 | `nfr-由来本文検査の-rule-id-体系を-nfr-id-check-で正式採用-台帳登録` | dd |
| DD-12 | `分析層-dfd-レベリング深化＋スタンプ結合排除の全面改訂` | dd |
| DD-13 | `mod-粒度の選択` | dd |
| DD-14 | `filesystemport-の抽象化粒度` | dd |
| DD-15 | `orc-の-must_link_to-参照先を-p-から-e-へ変更-設計ノードの上流参照の定義` | dd |
| DD-16 | `fnd-専用ライフサイクルルールを-config-に独立定義-q-4-から昇格・辺逆転の正式化` | dd |
| DD-17 | `config-駆動の-禁止接続-辺残留-検出に専用-rule-030-を新設-欠如-rule-006-と残存-rule-030-を責務` | dd |
| DD-18 | `resolved-の-boolean-型検証-spec-60-3-に専用-rule-031-を新設-共通必須型-rule-028-と型別任意型-rule-0` | dd |
| DD-19 | `検証戦略の段階別トリガを-§1-フロー図-l13-23-の単一トリガに統一-bump-非依存の辺残留検` | dd |
| DD-2 | `verify-の-rule-004-免除・fnd-は再検証シグナルとして据え置き-q-1-から昇格` | dd |
| DD-20 | `o-1-o-2-の生成元辺を親-p-4-からリーフ-p-4-3-へ精緻化-q-3-から昇格・o-生成元粒度のリーフ基` | dd |
| DD-21 | `resolved-fnd-辺逆転-backref-付与の版バンプ種別を-z-バンプに確定-q-5-から昇格・dd-8-§4-適用徹` | dd |
| DD-22 | `doc-system-設計層モデリングの-skill-展開方針を確定-q-6-から昇格・①-c-ハイブリッド／②-a` | dd |
| DD-3 | `fnd-起票時の-ref_version-本文記録ルール制度化` | dd |
| DD-4 | `分析層-ref_version-ドリフト群の一括解消-fnd-17-から昇格` | dd |
| DD-5 | `nfr-から-spec-導出を必須化する` | dd |
| DD-6 | `依存グラフレポート出力機能・参照関係複雑度算出の追加` | dd |
| DD-7 | `分析層ワークフロー改訂-図と並走してノード著作・d-は分析層で起票-＋-dfd-修正の技術決` | dd |
| DD-8 | `ノードバッジをノード固有バージョン-x.y.z-に正式化・ファイルフロントマター-version-廃` | dd |
| DD-9 | `config.yaml-phases-から-post-mvp-除去・rule-029-新設` | dd |
| DM-1 | `noderecord型` | dm |
| DM-2 | `edgerecord型` | dm |
| DM-3 | `violationrecord型` | dm |
| DM-4 | `configslice型群` | dm |
| DM-5 | `coveragereport型` | dm |
| DM-6 | `inspectionviews型群` | dm |
| DS-1 | `in-graph-ノードファイル群` | ds |
| DS-2 | `config.yaml-ds` | ds |
| DS-3 | `tmp-ノード草案` | ds |
| E-1 | `点検要求` | e |
| E-2 | `著作要求` | e |
| FND-1 | `actor-3-spec-inspector-の系境界誤り-被依存辺ゼロ` | fnd |
| FND-10 | `i-8-著作エージェント定義-の型分類誤り-i→p-7-内部` | fnd |
| FND-100 | `設計層の被覆チェーン-dm→mod→d-が-d-5-d-7-d-17〜d-21-経路で非対称-解消済み` | fnd |
| FND-101 | `resolved-済み-fnd-fnd-1〜95-が元の-forward-辺を削除せず辺逆転ルールに違反している` | fnd |
| FND-102 | `必須辺-config-44-行-のうち-dedicated-spec-を持つのは-8-行のみ・行→被覆-spec-のトレーサビリ` | fnd |
| FND-103 | `fnd_lifecycle-の必須辺ルール3つのうち-resolved-系2ルールに-dedicated-spec-が不在-被覆均一化の` | fnd |
| FND-104 | `config-駆動の-禁止接続-辺残留-must_not_link_to-を報告する-rule-が-05-verification.md-に未定義-検出` | fnd |
| FND-105 | `fnd-の-resolved-状態を機械判定するセマンティクス-resolved-フィールドの解釈-を定義した-in-g` | fnd |
| FND-106 | `検証戦略-05-verification.md-の段階別トリガ宣言がフロー図の単一トリガモデルと不整合-バッ` | fnd |
| FND-107 | `ノードバージョンの桁数定義が-2パート-x.y-と-3パート-x.y.z-で矛盾し-dd-8-§4-の-z-バンプが` | fnd |
| FND-108 | `_drift-が-x.y.z-フル比較で-z-バンプを誤ドリフト検出する-spec↔impl-乖離` | fnd |
| FND-109 | `03-spec.md-本文-例-記述-12-箇所に旧形式残存-バッジ-2-パート・ref_version-3-パート` | fnd |
| FND-11 | `e-1-に入力辺が欠如-イベントには入力が必ず伴う` | fnd |
| FND-110 | `fnd-96〜100-が-resolved-化-辺逆転のバンプを-minor-で記録し-dd-21-z-バンプ-に違反-a-1-以前の-pre` | fnd |
| FND-111 | `本文-resolved／機械-unresolved-の状態ドリフト-19-件-resolved-true-フラグ欠落・forward-辺残置` | fnd |
| FND-112 | `backref-check-の-open-but-backref-判定がトートロジーで-open-fnd-を全件誤検出する-github-issue-#64-cat` | fnd |
| FND-12 | `fr-1-の-spec-分割が荒く-yaml-不在・空集合・パース異常ケースが未定義` | fnd |
| FND-13 | `condition-語彙に空集合クラス-empty-が欠落し-null-ゼロ件を-boundary-normal-に混入していた` | fnd |
| FND-14 | `spec-本文がテスタブルでない-定量・一意・出力フォーマット欠如` | fnd |
| FND-15 | `fr-11-著作支援-が過積載でテンプレ-エージェント-ワークフロー-伝搬編集-エラー系が未分` | fnd |
| FND-16 | `fnd-1-の-forward-辺が削除済み-actor-3-を指して-dangling-rule-007-error` | fnd |
| FND-17 | `分析層の版上げに伴う-ref_version-ドリフト群-記録・義務辺含む・rule-004-warning` | fnd |
| FND-18 | `i-o-ノードのフォーマット定義が非公式散文にとどまり-spec-として機械検証不可` | fnd |
| FND-19 | `p-7-ノード著作プロセス-の単一責務違反-著作＋調停の2活動内包` | fnd |
| FND-2 | `p-2-rule-検査-の単一責務違反-粒度過大` | fnd |
| FND-20 | `p-1-受付・パース-にパース段検証-rule-023〜028-の責務記述がなく対応-spec-が無主` | fnd |
| FND-21 | `p-6-が-config.yaml-i-5-を-p-5-を経由せず直接読み込んでいる` | fnd |
| FND-22 | `プロセス間の内部データ-データディクショナリ-が-d-ノードとして未起票` | fnd |
| FND-23 | `p-7-1-に-actor-1-からの-ノード記載内容-入力が欠如し-o-3-を生成できない` | fnd |
| FND-24 | `h1-spec-14-1-rule-006-違反-fr-nfr-への直接辺なし` | fnd |
| FND-25 | `m1-spec-48-本文が-spec→spec-を有効と明記するが-config-はそれを強制しない矛盾` | fnd |
| FND-26 | `h2-docs-doc-system-03-connection-matrix.md-が-dd-5-と未同期で矛盾` | fnd |
| FND-27 | `h3-doc-system-03-analysis-00-dfd.md-が-out-of-graph-自称するが-trace_scope.exclude-に未登録` | fnd |
| FND-28 | `m2-spec-44〜54-spec-14-1-fr-15-16-追加バッチを対象とした-verify-が存在しない` | fnd |
| FND-29 | `m3-pr-#21-説明文が実変更と大きく乖離` | fnd |
| FND-3 | `events.md-の-e-2-欠番` | fnd |
| FND-30 | `m4-ダッシュボード-判断待ち-計-0-件-と-n1-記載の自己矛盾` | fnd |
| FND-31 | `l1-dd-影響範囲のバージョン注記が現在の-frontmatter-と乖離` | fnd |
| FND-32 | `l2-fr-1-ノードバッジ-v0.3-と-fr.md-ファイル-version-x.y=0.2-の不一致` | fnd |
| FND-33 | `l3-tmp-草稿に差し戻し済み-spec-41〜43-と旧-rule-028-定義が残存` | fnd |
| FND-34 | `verify-5-点検項目1-の事実誤記-sr-7-→-sr-2` | fnd |
| FND-35 | `config-の-spec→-fr,-nfr,-spec-or-規則のループホール` | fnd |
| FND-36 | `ノードバッジの意味が実態と矛盾-fnd-32-処置の誤定義・オーナー判断論点` | fnd |
| FND-37 | `tmp-草稿のコミット運用が継続されていない` | fnd |
| FND-38 | `pr-#22-説明文が実変更と大きく乖離-fnd-29-再発` | fnd |
| FND-39 | `dd-8-影響範囲に自己矛盾行残存-✅-完了-と-sprint-2-以降-が同居` | fnd |
| FND-4 | `カバレッジ点検-グラフ網羅性-の上流-spec-欠落` | fnd |
| FND-40 | `spec-1-期待動作が-生成・id一致・エラーなし-の複数アサーション混載でテスタブル基準違` | fnd |
| FND-41 | `spec-2-期待動作が-error出力・当該中断・後続不発火・他ファイル継続-の4動作混載` | fnd |
| FND-42 | `spec-3-2-期待動作が-idを永続させる・意味はheadingが担う-の2アサーション混載` | fnd |
| FND-43 | `spec-3-3-期待動作が-親→子辺は不要・親が存在すれば正常-の2アサーション混載` | fnd |
| FND-44 | `spec-6-期待動作が-rule-007-error報告-と-always_errorで抑制不可-の併載` | fnd |
| FND-45 | `spec-10-期待動作が-ドリフト検出・再反映を促す-の2動詞混載` | fnd |
| FND-46 | `spec-12-期待動作が-error報告・dd→x削除・x→dd追加-の3動作混載` | fnd |
| FND-47 | `spec-14-1-期待動作が-ヘッダ行出力・各行出力-＋別フィールド展開で複数アサーション` | fnd |
| FND-48 | `spec-21-1-期待動作が-評価をスキップ・違反を報告しない-の2動詞混載` | fnd |
| FND-49 | `spec-21-2-期待動作が-元の深刻度で評価・違反があれば報告-の2動詞混載` | fnd |
| FND-5 | `fr-6-本文が廃止-rule-015-を生きた番号として参照` | fnd |
| FND-50 | `spec-21-3-期待動作が-抑制設定を無視・error報告-＋rule-007-005の2目的語混載` | fnd |
| FND-51 | `spec-21-4-期待動作が-設定エラー報告・判定スキップ・全ルール評価-の3動作混載` | fnd |
| FND-52 | `spec-23-1-期待動作が-抑制を無視・常にerror報告-の2動詞＋rule-007-005併記` | fnd |
| FND-53 | `spec-26-期待動作が-テンプレ全項目包含・複製で-rule-025-026-027-不発火-の2アサーション＋多` | fnd |
| FND-54 | `spec-27-期待動作が-type値-id-prefix-必須辺方向-本文4項目-ruleチェックリスト-の5目的語を1動` | fnd |
| FND-55 | `spec-28-期待動作が-realizes辺照合・設計漏れと紐づけ漏れ検出-の2動作・2目的語混載` | fnd |
| FND-56 | `spec-29-期待動作が-0件で通過・価値経路と分析層接続充足と判定-の2動作混載` | fnd |
| FND-57 | `spec-30-期待動作が-未駆動出力-未定義反応イベント-未消費入力-の3目的語を1報告に混載` | fnd |
| FND-58 | `spec-31-期待動作が-違反0-ノード0報告・exit-0・rule全スキップ-の3動作混載` | fnd |
| FND-59 | `spec-32-期待動作が-error出力・ファイル中断-の2動作混載` | fnd |
| FND-6 | `i-1-1-i-1-2-i-1-3-の過分割の疑い` | fnd |
| FND-60 | `spec-33-期待動作が-error出力・後続rule中断-の2動作混載` | fnd |
| FND-61 | `spec-34-期待動作が-error出力・後続rule中断-の2動作混載` | fnd |
| FND-62 | `spec-35-期待動作が-error出力・後続rule中断-の2動作混載` | fnd |
| FND-63 | `spec-36-期待動作が-rule-025-id欠如-または-rule-026-type欠如-の選言目的語混載` | fnd |
| FND-64 | `spec-38-期待動作が-ノードをtmp出力・reconciliationが転記-の2主体・2動作混載` | fnd |
| FND-65 | `spec-39-期待動作が-検証エラー報告・転記中断・id-field-missing出力-の3動作混載` | fnd |
| FND-66 | `spec-40-期待動作が-一覧を表形式で出力・-形式-で表示-の2文混載` | fnd |
| FND-67 | `spec-44-期待動作が-読込完了・bomはwarning・デコードエラーはerror-の3分岐混載` | fnd |
| FND-68 | `spec-45-期待動作が-全importが標準ライブラリのみ・外部依存0件-＋違反出力で複数アサーシ` | fnd |
| FND-69 | `spec-46-期待動作が-外部参照パターン非存在・0件確認・検証通過-の複数動作混載` | fnd |
| FND-7 | `e-2-スティミュラスが-新規ノード著作-のみで既存ノード改訂を含まない` | fnd |
| FND-70 | `spec-47-期待動作が-version存在・形式適合-と-欠如-空-nullはerror-の正負2分岐混載` | fnd |
| FND-71 | `spec-48-期待動作が-全辺がfr-nfr-specを指す・祖先辺0件・検出時error-の複数アサーション混載` | fnd |
| FND-72 | `spec-49-期待動作が-status系キー非存在・存在でwarning・状態は本文バッジ-の複数アサーショ` | fnd |
| FND-73 | `spec-50-期待動作が-指定フォーマットでファイル出力・stdoutエラーなし・exit-0-の3動作混載` | fnd |
| FND-74 | `spec-51-期待動作が-メトリクスレポートstdout出力・exit-0-の2動作混載` | fnd |
| FND-75 | `spec-52-期待動作が-rule-025-026-027-028非発火・終了コード0-の2アサーション混載` | fnd |
| FND-76 | `spec-53-期待動作が-rule-028-error-1件出力・後続rule中断-の2動作混載` | fnd |
| FND-77 | `spec-54-期待動作が-i-7-i-9充填し草案生成・i-9なしでo-3生成不可・テンプレのみ生成不可保` | fnd |
| FND-78 | `spec-50-51-の-post-mvp-と-scheduled-表現が不統一-オーナー決定bで-config-改訂方針` | fnd |
| FND-79 | `rule-006-025-026-が複数-spec-に分散し全体把握の負荷-＋横断スパイン-✅-表記矛盾の索引精度` | fnd |
| FND-8 | `d-2-著作済みノードファイル-の型分類誤り-d→o` | fnd |
| FND-80 | `pend-義務辺残存-rule-022-に対応する-failure-spec-が不在` | fnd |
| FND-81 | `spec-31-の親が-fr-1-だが-trace_scope-主題の-fr-9-が自然` | fnd |
| FND-82 | `spec-9-1-と-spec-10-が同一-rule-004-検出でほぼ同主張` | fnd |
| FND-83 | `always_error-系-spec-の-condition-が不揃い-spec-6=error,-spec-7=failure` | fnd |
| FND-84 | `spec-47-spec-44-が-dd-8-ファイル-frontmatter-全廃-と矛盾` | fnd |
| FND-85 | `spec-49-1-49-2-が廃止済み-frontmatter-を検査対象にしている-dd-8-矛盾` | fnd |
| FND-86 | `nfr-由来本文検査の出力ルール-id-規約が未定義-nfr-id-check-vs-rule-nnn` | fnd |
| FND-87 | `spec-30-に分析層-d-の接続漏れ失敗系子が欠落` | fnd |
| FND-88 | `spec-13-の期待動作が条件節文頭のテスタブル様式に整っていない` | fnd |
| FND-89 | `傘-spec-の-condition-が子の-condition-多様性を代表せずミスリード` | fnd |
| FND-9 | `i-6-候補ファイルパス一覧-の名称が内容を表していない` | fnd |
| FND-90 | `検証手順の観測-実行主体が二者択一で一意でない-再現性・観測可能性` | fnd |
| FND-91 | `spec-3-1-が人手の-id-採番行為を期待動作とし機械観測が難しい＋例の欠落` | fnd |
| FND-92 | `e-1-点検要求-本文が-p-8-p-9・o-4-o-5-を反映していない不整合` | fnd |
| FND-93 | `d-4-構造化ノードセット-定義が-condition-result-log_ref-を欠き-p-2-3-p-2-4-p-3-2-の入力が台帳上断` | fnd |
| FND-94 | `分析層全面見直し起因の被覆ドリフト-2-件-g1-孤児-spec・g4-旧-p-3-消費先記述残存` | fnd |
| FND-95 | `p-4-4-終了コード決定-の終端出力-終了コード-0-1-が-o-d-ノード化されず価値経路が受け手に` | fnd |
| FND-96 | `設計層の接続チェーン-dm→mod→d-が欠落しており-mod→p-dm→p-の強制が-pr1-違反を生む` | fnd |
| FND-97 | `orc-1-frontmatter-の-p-辺が-dd-15-決定に反する-解消済み` | fnd |
| FND-98 | `ダッシュボード・pr-本文が-dd-13-v0.2-改訂前のスナップショットで陳腐化` | fnd |
| FND-99 | `設計接続規則の決定-fnd-96・dd-15-が-out-of-graph-著作資産に未伝播` | fnd |
| FR-1 | `ノードグラフの構造化表現` | fr |
| FR-10 | `検証ツールの実行形態` | fr |
| FR-11 | `テンプレートによる著作品質保証` | fr |
| FR-12 | `コード⇔設計の構造比較-段階④・post-mvp` | fr |
| FR-13 | `著作エージェントと層ワークフロー` | fr |
| FR-14 | `伝搬編集支援-post-mvp` | fr |
| FR-15 | `依存グラフレポート出力` | fr |
| FR-16 | `参照関係複雑度算出` | fr |
| FR-17 | `skill-の-llm-プロンプト資産モデリング-機能軸` | fr |
| FR-2 | `id-体系と階層分解` | fr |
| FR-3 | `構造的完結性検証` | fr |
| FR-4 | `バージョンドリフト検出` | fr |
| FR-5 | `意思決定ドリフト検出` | fr |
| FR-6 | `仕様カバレッジ検証` | fr |
| FR-7 | `検証・指摘の完結性検証` | fr |
| FR-8 | `三軸の検査抑制機構` | fr |
| FR-9 | `トレース対象集合の宣言` | fr |
| I-1 | `ノードファイル群` | i |
| I-5 | `config.yaml-i` | i |
| I-6 | `ディレクトリ走査-.md-ファイルパス一覧` | i |
| I-7 | `テンプレートファイル群` | i |
| I-9 | `ノード記載内容` | i |
| MOD-1 | `domain` | mod |
| MOD-10 | `ports` | mod |
| MOD-11 | `adapters-fs` | mod |
| MOD-12 | `__main__` | mod |
| MOD-13 | `projector` | mod |
| MOD-14 | `structure_checker` | mod |
| MOD-15 | `condition_checker` | mod |
| MOD-16 | `verification_checker` | mod |
| MOD-17 | `spec_coverage` | mod |
| MOD-18 | `reconciler` | mod |
| MOD-2 | `config` | mod |
| MOD-3 | `collector` | mod |
| MOD-4 | `parser` | mod |
| MOD-5 | `drift_checker` | mod |
| MOD-6 | `filter` | mod |
| MOD-7 | `graph_coverage` | mod |
| MOD-8 | `reporter` | mod |
| MOD-9 | `author` | mod |
| NFR-1 | `プレーンテキスト形式` | nfr |
| NFR-2 | `標準ライブラリのみでパース可能` | nfr |
| NFR-3 | `スキルは-self-contained` | nfr |
| NFR-4 | `ファイル単位バージョニング・1-ファイル-1-責務` | nfr |
| NFR-5 | `直接の親-1-段のみ・usdm-分割` | nfr |
| NFR-6 | `ライフサイクル状態は本文・メタに持たない` | nfr |
| O-1 | `rule-違反レポート` | o |
| O-2 | `カバレッジ点検結果` | o |
| O-3 | `著作済みノードファイル` | o |
| O-4 | `依存グラフ出力ファイル` | o |
| O-5 | `参照関係複雑度メトリクスレポート` | o |
| O-6 | `終了コード` | o |
| ORC-1 | `検査パイプライン実行` | orc |
| ORC-2 | `著作・反映パイプライン実行` | orc |
| P-1 | `ノード受付・パース` | p |
| P-1-1 | `ファイル読込` | p |
| P-1-2 | `マーカー走査` | p |
| P-1-3 | `yaml-パース` | p |
| P-1-4 | `スキーマ検証-p-1-4` | p |
| P-1-5 | `構造化集合組立` | p |
| P-1-6 | `検査ビュー射影` | p |
| P-2 | `rule-検査` | p |
| P-2-1 | `ドリフト・義務辺検査` | p |
| P-2-1-1 | `ref_version-ドリフト検出` | p |
| P-2-1-2 | `決定スパイン義務辺残存検出` | p |
| P-2-2 | `構造完結性検査` | p |
| P-2-2-1 | `孤立ノード検出` | p |
| P-2-2-2 | `存在しない-id-参照検出` | p |
| P-2-2-3 | `必須辺欠如検出` | p |
| P-2-2-4 | `階層親不在検出` | p |
| P-2-3 | `カバレッジ属性検査` | p |
| P-2-3-1 | `condition-属性・語彙検査` | p |
| P-2-3-2 | `fr-normal-spec-網羅検査` | p |
| P-2-3-3 | `fr-failure-error-spec-網羅検査` | p |
| P-2-3-4 | `td-spec-condition-整合検査` | p |
| P-2-4 | `検証層完結性検査` | p |
| P-2-4-1 | `fnd-tc-verify-必須辺検査` | p |
| P-2-4-2 | `tr-result-属性検査` | p |
| P-2-4-3 | `tr-log_ref-属性検査` | p |
| P-2-5 | `抑制・発火フィルタ` | p |
| P-3 | `カバレッジ点検` | p |
| P-3-1 | `グラフ網羅性点検` | p |
| P-3-1-1 | `未駆動出力検出` | p |
| P-3-1-2 | `未定義反応イベント検出` | p |
| P-3-1-3 | `未消費入力検出` | p |
| P-3-2 | `仕様カバレッジ計測` | p |
| P-3-2-1 | `fr×condition-充足集計` | p |
| P-3-2-2 | `テーブル整形・fr-id-昇順出力` | p |
| P-4 | `レポート生成` | p |
| P-4-1 | `違反レコード統合` | p |
| P-4-2 | `深刻度順整列` | p |
| P-4-3 | `g-番号付与・整形` | p |
| P-4-4 | `終了コード決定` | p |
| P-5 | `設定ファイル読み込み` | p |
| P-5-1 | `config-読込` | p |
| P-5-2 | `スキーマ検証-p-5-2` | p |
| P-5-3 | `設定スライス組立` | p |
| P-6 | `in-graph-集合決定` | p |
| P-6-1 | `include-一致抽出` | p |
| P-6-2 | `exclude-除外適用` | p |
| P-7 | `ノード著作・反映プロセス` | p |
| P-7-1 | `著作・tmp-出力` | p |
| P-7-1-1 | `テンプレート取得` | p |
| P-7-1-2 | `記載内容充填` | p |
| P-7-1-3 | `草案-tmp-書出` | p |
| P-7-2 | `調停・本ファイル反映` | p |
| P-7-2-1 | `草案スキーマ検証` | p |
| P-7-2-2 | `本ファイル転記` | p |
| P-8 | `依存グラフ出力処理` | p |
| P-9 | `参照関係複雑度計算処理` | p |
| PEND-1 | `i-1-1-i-1-2-i-1-3-の独立入力化の妥当性-pr1-過分割の疑い` | pend |
| PEND-2 | `分析層の図-コンテキスト図・dfd-の手動メンテをスクリプト自動生成へ置換-先送り` | pend |
| PORT-1 | `filesystemport` | port |
| PROMPT-1 | `requirements-author-著作支援プロンプト-val-sr-fr-nfr` | prompt |
| PROMPT-10 | `mvp-scope-価値ベースmvpスコープskillプロンプト` | prompt |
| PROMPT-11 | `schema-design-スキーマ設計skillプロンプト-読み手から決める` | prompt |
| PROMPT-12 | `domain-model-ドメインモデル設計skillプロンプト-データ辞書→型安全なクラス` | prompt |
| PROMPT-13 | `architecture-design-アーキテクチャ設計skillプロンプト-論理dfd→物理モジュール-依存・if・プ` | prompt |
| PROMPT-14 | `orchestration-design-オーケストレーション設計skillプロンプト-制御フロー・fail-close・ログ-版` | prompt |
| PROMPT-15 | `prompt-design-プロンプト設計skillプロンプト-llmへの問い方を固める` | prompt |
| PROMPT-16 | `test-strategy-テスト戦略skillプロンプト-review-system-テーラリング済` | prompt |
| PROMPT-17 | `spec-principles-仕様設計・点検の原則skillプロンプト-pr1–pr10` | prompt |
| PROMPT-18 | `spec-pipeline-仕様設計パイプラインskillプロンプト-オーケストレータ` | prompt |
| PROMPT-19 | `impl-design-pipeline-実装設計パイプラインskillプロンプト-凍結セット化` | prompt |
| PROMPT-2 | `spec-author-著作支援プロンプト-spec・1アサーション1ノード` | prompt |
| PROMPT-20 | `asset-pipeline-資産化パイプラインskillプロンプト-method→skill-agent` | prompt |
| PROMPT-3 | `analysis-author-著作支援プロンプト-actor-i-o-d-p-e` | prompt |
| PROMPT-4 | `design-author-著作支援プロンプト-orc-ds-mod-dm-port-prs-scm-cfg-prompt-term` | prompt |
| PROMPT-5 | `verification-author-著作支援プロンプト-td-tc-tr-verify-fnd-dd-q-pend` | prompt |
| PROMPT-6 | `reconciliation-調停支援プロンプト-検証＋本ファイル転記` | prompt |
| PROMPT-7 | `reconciliation-validator-検証支援プロンプト-read-only-構造検証・validation_ok-rollback` | prompt |
| PROMPT-8 | `align-認識合わせスキルプロンプト-着手前の段取り` | prompt |
| PROMPT-9 | `value-trace-価値経路トレースskillプロンプト-イベント総点検` | prompt |
| PRS-1 | `tmp-草案ファイル書き出し` | prs |
| Q-1 | `凍結記録-verify・解消済み-fnd-の-ref_version-ドリフト扱い` | q |
| Q-2 | `リーフプロセスの-spec-1-1-不足-傘-spec-暫定マップ-—-要件層で-spec-を細分化するか傘マッ` | q |
| Q-3 | `o-1・o-2-の生成元辺が親-p-4-のまま-—-リーフ精緻化-→p-4-3-するか親許容か` | q |
| Q-4 | `fnd-専用ライフサイクルルールを汎用-rule-006-から独立定義すべきか-辺の逆転の正式化` | q |
| Q-5 | `resolved-fnd-辺逆転の版バンプ-minor-か-z-か-／backref・provenance-辺を-rule-004-ドリフト対象外と` | q |
| Q-6 | `doc-system-設計層モデリングを-skill-資産へどう広げるか-—-①pipeline-skill-のオーケストレー` | q |
| SCM-1 | `ノードフォーマットスキーマ` | scm |
| SCM-1-1 | `ノード-yaml-ブロックスキーマ` | scm |
| SCM-1-2 | `ノードファイル記法スキーマ` | scm |
| SCM-2 | `config.yaml-スキーマ` | scm |
| SCM-2-1 | `接続ルールスキーマ` | scm |
| SCM-2-2 | `ライフサイクル／決定スパインスキーマ` | scm |
| SCM-2-3 | `ステージ／語彙／カバレッジ／スコープスキーマ` | scm |
| SCM-3 | `出力フォーマットスキーマ` | scm |
| SCM-3-1 | `rule-違反レポート行形式` | scm |
| SCM-3-2 | `カバレッジ結果形式` | scm |
| SPEC-1 | `ノード埋め込みのパース` | spec |
| SPEC-1-1 | `構造化ノード1件の生成` | spec |
| SPEC-1-2 | `マーカー-prefix-n-と-yaml-id-の一致検証` | spec |
| SPEC-1-3 | `パース段違反なし-→-エラー出力なし` | spec |
| SPEC-10 | `ファイル-x.y-上昇で依存辺をドリフト検出` | spec |
| SPEC-10-1 | `ref_version-不一致を-rule-004-error-検出` | spec |
| SPEC-10-2 | `ドリフト検出時に再反映を促すメッセージを出力` | spec |
| SPEC-11 | `意思決定が全反映済みなら漏れ-0` | spec |
| SPEC-12 | `dd-の義務辺残存` | spec |
| SPEC-13 | `q-の義務辺残存` | spec |
| SPEC-14 | `カバレッジレポートの生成` | spec |
| SPEC-14-1 | `カバレッジテーブルの出力フォーマット` | spec |
| SPEC-14-1-1 | `カバレッジテーブルのヘッダ行出力` | spec |
| SPEC-14-1-2 | `各-fr-行のセル値出力` | spec |
| SPEC-14-1-3 | `明細行を-fr-id-昇順でソート出力` | spec |
| SPEC-14-1-4 | `正常出力時の終了コード-0` | spec |
| SPEC-15 | `spec×td-カバレッジ・condition-不整合` | spec |
| SPEC-15-1 | `spec-に-td-からの被依存辺欠如-rule-006` | spec |
| SPEC-15-2 | `condition-属性なし・語彙外-rule-016` | spec |
| SPEC-15-3 | `td-の-condition-が-verifies-先-spec-と不一致-rule-019` | spec |
| SPEC-16 | `fr-の-condition-網羅` | spec |
| SPEC-16-1 | `fr-の-spec-群に-normal-condition-なし-rule-017` | spec |
| SPEC-16-2 | `fr-の-spec-群に-failure-error-condition-なし-rule-018` | spec |
| SPEC-17 | `検証層の辺・属性が揃えば違反-0` | spec |
| SPEC-18 | `検証層ノードの必須辺欠如` | spec |
| SPEC-18-1 | `fnd-に被指摘要素への辺欠如-rule-006` | spec |
| SPEC-18-2 | `tc-がテスト未実行-tr-不在-rule-006` | spec |
| SPEC-18-3 | `nfr-に検証証跡の被依存辺欠如-rule-006` | spec |
| SPEC-18-4 | `tc-に-td-への依存辺欠如-rule-006` | spec |
| SPEC-18-5 | `verify-に対象要素への依存辺欠如-rule-006` | spec |
| SPEC-18-6 | `td-に-spec-への依存辺欠如-rule-006` | spec |
| SPEC-18-7 | `tr-に-tc-への依存辺欠如-rule-006` | spec |
| SPEC-18-8 | `td-に-tc-からの被依存辺欠如-rule-006` | spec |
| SPEC-18-9 | `解消済み-fnd-に処置対象からの被依存辺欠如-rule-006` | spec |
| SPEC-19 | `テスト結果の完結性` | spec |
| SPEC-19-1 | `tr-に-result-属性なし-rule-020` | spec |
| SPEC-19-2 | `tr-に-log_ref-なし-result-問わず-rule-021` | spec |
| SPEC-2 | `記法が崩れた-yaml-ブロックのパース失敗` | spec |
| SPEC-2-1 | `yaml-構文不正で-rule-023-error-を出力` | spec |
| SPEC-2-2 | `yaml-構文不正で当該ファイルのパースを中断` | spec |
| SPEC-2-3 | `パース中断後は後続-rule-024〜027-を発火させない` | spec |
| SPEC-2-4 | `当該ファイル中断後も他-in-graph-ファイルの処理を継続` | spec |
| SPEC-20 | `scheduled-による完全サイレント` | spec |
| SPEC-21 | `ステージ発火による検査制御` | spec |
| SPEC-21-1 | `発火ステージ未達のルールはサイレント` | spec |
| SPEC-21-1-1 | `発火ステージ未達のルールは評価をスキップ` | spec |
| SPEC-21-1-2 | `発火ステージ未達のルールは違反を報告しない` | spec |
| SPEC-21-2 | `発火ステージ到達でルール発火` | spec |
| SPEC-21-2-1 | `発火ステージ到達でルールを元の深刻度で評価` | spec |
| SPEC-21-2-2 | `発火したルールの違反を報告` | spec |
| SPEC-21-3 | `always_error-は発火ステージ前でも発火` | spec |
| SPEC-21-3-1 | `always_error-の-rule-007-は発火ステージ前でも-error-報告` | spec |
| SPEC-21-3-2 | `always_error-の-rule-005-は発火ステージ前でも-error-報告` | spec |
| SPEC-21-4 | `current_stage-が-stages-に未定義` | spec |
| SPEC-21-4-1 | `current_stage-未定義でツール設定エラーを報告` | spec |
| SPEC-21-4-2 | `current_stage-未定義でステージ発火判定をスキップ` | spec |
| SPEC-21-4-3 | `current_stage-未定義時は全ルールを元の深刻度で評価` | spec |
| SPEC-22 | `suppress-による理由付きルール抑制` | spec |
| SPEC-23 | `suppress-の禁止ケース` | spec |
| SPEC-23-1 | `rule-007-005-を-suppress-に含めても抑制不可` | spec |
| SPEC-23-1-1 | `suppress-に-rule-007-を含めても-error-報告` | spec |
| SPEC-23-1-2 | `suppress-に-rule-005-を含めても-error-報告` | spec |
| SPEC-23-2 | `suppress-エントリに理由コメントなし` | spec |
| SPEC-24 | `trace_scope-による-in-graph-判定` | spec |
| SPEC-24-1 | `include-一致・exclude-非一致-→-in-graph` | spec |
| SPEC-24-2 | `include-一致・exclude-一致-→-out-of-graph` | spec |
| SPEC-25 | `出力形式と終了コード` | spec |
| SPEC-25-1 | `違反一覧の深刻度順整列` | spec |
| SPEC-25-2 | `error-あり-→-終了コード-1` | spec |
| SPEC-25-3 | `error-なし-→-終了コード-0` | spec |
| SPEC-26 | `テンプレートの必須フィールド充足` | spec |
| SPEC-26-1 | `テンプレートが必須フィールドを全て含む` | spec |
| SPEC-26-2 | `複製直後に-rule-025-が不発火` | spec |
| SPEC-26-3 | `複製直後に-rule-026-が不発火` | spec |
| SPEC-26-4 | `複製直後に-rule-027-が不発火` | spec |
| SPEC-27 | `著作エージェントが外部参照なしに著作規約を提供` | spec |
| SPEC-27-1 | `エージェントが外部参照なしに-type-値を提供` | spec |
| SPEC-27-2 | `エージェントが外部参照なしに-id-prefix-パターンを提供` | spec |
| SPEC-27-3 | `エージェントが外部参照なしに必須辺方向を提供` | spec |
| SPEC-27-4 | `エージェントが外部参照なしに本文4項目フォーマットを提供` | spec |
| SPEC-27-5 | `エージェントが外部参照なしに-rule-チェックリストを提供` | spec |
| SPEC-28 | `src-の-@id-realizes-検証` | spec |
| SPEC-28-1 | `realizes-照合で設計漏れを検出` | spec |
| SPEC-28-2 | `realizes-照合で紐づけ漏れを検出` | spec |
| SPEC-28-3 | `src-に-dm-port-orc-への必須辺欠如-rule-006` | spec |
| SPEC-29 | `グラフ網羅性点検の正常系` | spec |
| SPEC-29-1 | `孤立・必須辺欠如のゼロ件通過` | spec |
| SPEC-29-2 | `価値経路到達の充足判定` | spec |
| SPEC-3 | `id-管理の正常系` | spec |
| SPEC-3-1 | `prefix-n-n...-形式の一意-id-採番` | spec |
| SPEC-3-2 | `id-の永続-リネームなし` | spec |
| SPEC-3-2-1 | `内容変更時も-id-を永続させる` | spec |
| SPEC-3-2-2 | `意味は-heading-が担い-id-は追跡キーに限定` | spec |
| SPEC-3-3 | `階層-id-の親ノード存在` | spec |
| SPEC-3-3-1 | `階層は-id-パターンから推論し親→子辺を要求しない` | spec |
| SPEC-3-3-2 | `親ノードが存在すれば階層-id-を正常と判定` | spec |
| SPEC-30 | `分析ノードの接続漏れ検出` | spec |
| SPEC-30-1 | `未駆動出力-o→p-欠如-の検出` | spec |
| SPEC-30-2 | `未定義反応イベント-e←p-欠如-の検出` | spec |
| SPEC-30-3 | `未消費入力-i←p-欠如-の検出` | spec |
| SPEC-31 | `trace_scope-による-in-graph-0-件` | spec |
| SPEC-31-1 | `in-graph-0-件で違反0件を報告` | spec |
| SPEC-31-2 | `in-graph-0-件で終了コード-0` | spec |
| SPEC-31-3 | `in-graph-0-件で-rule-評価を全スキップ` | spec |
| SPEC-31-4 | `in-graph-0-件でノード0件を報告` | spec |
| SPEC-32 | `⬡-マーカー直後に-yaml-ブロックなし` | spec |
| SPEC-32-1 | `⬡-マーカー直後-yaml-欠如で-rule-024-error-出力` | spec |
| SPEC-32-2 | `⬡-マーカー直後-yaml-欠如で当該ファイルのパース中断` | spec |
| SPEC-33 | `id-フィールド欠如・空` | spec |
| SPEC-33-1 | `id-欠如時に-rule-025-error-を出力` | spec |
| SPEC-33-2 | `id-欠如時に当該ノードの後続-rule-評価を中断` | spec |
| SPEC-34 | `type-フィールド欠如・空` | spec |
| SPEC-34-1 | `type-欠如時に-rule-026-error-を出力` | spec |
| SPEC-34-2 | `type-欠如時に当該ノードの後続-rule-評価を中断` | spec |
| SPEC-35 | `edge-に-ref_version-欠如` | spec |
| SPEC-35-1 | `edge-の-ref_version-欠如時に-rule-027-error-を出力` | spec |
| SPEC-35-2 | `edge-の-ref_version-欠如時に当該ノードの後続-rule-評価を中断` | spec |
| SPEC-36 | `テンプレート由来の必須フィールド欠如` | spec |
| SPEC-36-1 | `テンプレート由来-id-欠如時に-rule-025-error-を報告` | spec |
| SPEC-36-2 | `テンプレート由来-type-欠如時に-rule-026-error-を報告` | spec |
| SPEC-38 | `著作エージェント出力と-reconciliation-転記` | spec |
| SPEC-38-1 | `著作エージェントが規約準拠ノードを-tmp-出力` | spec |
| SPEC-38-2 | `reconciliation-が-tmp-出力を本ファイルに転記` | spec |
| SPEC-39 | `著作出力の-id-欠如検出時の-reconciliation-挙動` | spec |
| SPEC-39-1 | `id-欠如-tmp-出力に-reconciliation-が検証エラーを報告` | spec |
| SPEC-39-2 | `id-欠如検出時に-rule-025-相当メッセージを出力` | spec |
| SPEC-39-3 | `id-欠如検出時に-reconciliation-が転記を中断` | spec |
| SPEC-4 | `階層-id-親ノードの不在` | spec |
| SPEC-40 | `伝搬編集支援の表示` | spec |
| SPEC-40-1 | `伝搬時にドリフトノード一覧を表形式で出力` | spec |
| SPEC-40-2 | `ドリフト一覧の各行を更新フォーマットで表示` | spec |
| SPEC-44 | `ノードファイルはプレーンテキスト-.md` | spec |
| SPEC-44-1 | `正常-utf-8-ファイルの読み込みが完了` | spec |
| SPEC-44-2 | `bom-付きファイルに-warning-を1件出力` | spec |
| SPEC-44-3 | `utf-8-デコードエラー発生ファイルに-error-を1件出力` | spec |
| SPEC-45 | `spec-inspector-は-python-標準ライブラリのみ使用` | spec |
| SPEC-45-1 | `全-import-が標準ライブラリのみを参照する` | spec |
| SPEC-45-2 | `外部パッケージ-import-検出時に-error-を出力する` | spec |
| SPEC-46 | `スキルファイルは外部ファイル参照なしに自己完結` | spec |
| SPEC-46-1 | `スキルファイルに外部参照パターンが存在しない` | spec |
| SPEC-46-2 | `外部参照パターン検出時に-warning-を出力する` | spec |
| SPEC-47 | `全-in-graph-ノードの-summary-バッジに-version-x.y.z-が存在する` | spec |
| SPEC-47-1 | `全ノードのバッジが-·-vx.y.z-非負整数-3-部-形式を持つ` | spec |
| SPEC-47-2 | `バッジ-version-欠如・形式不正のノードに-error-を出力する` | spec |
| SPEC-48 | `各ノードは直接の親のみへ辺を張る-usdm-1段制約` | spec |
| SPEC-48-1 | `spec-の辺が全て直接親型-fr-nfr-spec-を指す` | spec |
| SPEC-48-2 | `祖先型への直接辺検出時に-error-を出力する` | spec |
| SPEC-49 | `dd-q-pend-のノード-yaml-メタ属性-に-status-系フィールドが存在しない` | spec |
| SPEC-49-1 | `status-系キー非存在ノードは違反なし` | spec |
| SPEC-49-2 | `status-系キー存在で-warning-出力` | spec |
| SPEC-5 | `整合グラフは構造違反-0-で通過` | spec |
| SPEC-50 | `export-graph-による依存グラフファイル出力` | spec |
| SPEC-50-1 | `export-graph-で指定フォーマットのグラフファイルを生成` | spec |
| SPEC-50-2 | `export-graph-正常時-stdout-にエラーを出力しない` | spec |
| SPEC-50-3 | `export-graph-正常時-exit-code-0-で終了` | spec |
| SPEC-51 | `complexity-による参照関係複雑度メトリクスレポート-stdout-出力` | spec |
| SPEC-51-1 | `complexity-でメトリクスレポートを-stdout-出力` | spec |
| SPEC-51-2 | `complexity-正常時-exit-code-0-で終了` | spec |
| SPEC-52 | `i-1-完全フィールドスキーマ適合` | spec |
| SPEC-52-1 | `完全スキーマ適合ノードは-rule-025-を発火させない` | spec |
| SPEC-52-2 | `完全スキーマ適合ノードは-rule-026-を発火させない` | spec |
| SPEC-52-3 | `完全スキーマ適合ノードは-rule-027-を発火させない` | spec |
| SPEC-52-4 | `完全スキーマ適合ノードは-rule-028-を発火させない` | spec |
| SPEC-52-5 | `スキーマ違反-0-件のとき終了コード-0` | spec |
| SPEC-53 | `共通必須フィールドの型不正・欠如検出` | spec |
| SPEC-53-1 | `共通必須フィールド違反の-error-出力` | spec |
| SPEC-53-2 | `共通必須フィールド違反ノードの後続-rule-中断` | spec |
| SPEC-53-3 | `共通必須フィールド違反時のプロセス終了コード` | spec |
| SPEC-54 | `著作は記載内容入力を必須とする` | spec |
| SPEC-54-1 | `著作は-i-7-と-i-9-を充填して草案を生成する` | spec |
| SPEC-54-2 | `i-9-欠如時は-o-3-を生成しない` | spec |
| SPEC-54-3 | `i-7-のみでは-o-3-を生成しない` | spec |
| SPEC-55 | `pend-の義務辺残存` | spec |
| SPEC-56 | `要件層ノードの必須辺欠如` | spec |
| SPEC-56-1 | `sr-に-val-への依存辺欠如-rule-006` | spec |
| SPEC-56-2 | `fr-に-sr-への依存辺欠如-rule-006` | spec |
| SPEC-56-3 | `nfr-に-sr-への依存辺欠如-rule-006` | spec |
| SPEC-56-4 | `spec-に-fr-nfr-spec-への依存辺欠如-rule-006` | spec |
| SPEC-56-5 | `val-に-sr-からの被依存辺欠如-rule-006` | spec |
| SPEC-56-6 | `sr-に-fr-nfr-actor-からの被依存辺欠如-rule-006` | spec |
| SPEC-56-7 | `fr-に-spec-からの被依存辺欠如-rule-006` | spec |
| SPEC-56-8 | `nfr-に-spec-からの被依存辺欠如-rule-006` | spec |
| SPEC-57 | `分析層ノードの必須辺欠如-価値経路3種以外` | spec |
| SPEC-57-1 | `actor-に-sr-への依存辺欠如-rule-006` | spec |
| SPEC-57-10 | `e-に-actor-への依存辺欠如-rule-006` | spec |
| SPEC-57-11 | `actor-に-e-i-o-からの被依存辺欠如-rule-006` | spec |
| SPEC-57-12 | `d-に-p-からの被依存辺欠如-rule-006` | spec |
| SPEC-57-2 | `term-に-spec-への依存辺欠如-rule-006` | spec |
| SPEC-57-3 | `i-に-spec-への依存辺欠如-rule-006` | spec |
| SPEC-57-4 | `o-に-spec-への依存辺欠如-rule-006` | spec |
| SPEC-57-5 | `o-に-actor-への依存辺欠如-rule-006` | spec |
| SPEC-57-6 | `d-に-spec-への依存辺欠如-rule-006` | spec |
| SPEC-57-7 | `d-に-p-への依存辺欠如-rule-006` | spec |
| SPEC-57-8 | `p-に-spec-への依存辺欠如-rule-006` | spec |
| SPEC-57-9 | `e-に-spec-への依存辺欠如-rule-006` | spec |
| SPEC-58 | `設計層ノードの必須辺欠如検出` | spec |
| SPEC-58-1 | `orc-に-e-への依存辺欠如-rule-006` | spec |
| SPEC-58-10 | `cfg-に-spec-への依存辺欠如-rule-006` | spec |
| SPEC-58-11 | `prompt-に-spec-への依存辺欠如-rule-006` | spec |
| SPEC-58-12 | `e-に-orc-からの被依存辺欠如-rule-006` | spec |
| SPEC-58-2 | `ds-に-p-への依存辺欠如-rule-006` | spec |
| SPEC-58-3 | `mod-に-p-d-への依存辺欠如-rule-006` | spec |
| SPEC-58-4 | `dm-に-term-への依存辺欠如-rule-006` | spec |
| SPEC-58-5 | `dm-に-mod-への依存辺欠如-rule-006` | spec |
| SPEC-58-6 | `port-に-mod-への依存辺欠如-rule-006` | spec |
| SPEC-58-7 | `prs-に-ds-への依存辺欠如-rule-006` | spec |
| SPEC-58-8 | `scm-に-spec-への依存辺欠如-rule-006` | spec |
| SPEC-58-9 | `cfg-に-scm-への依存辺欠如-rule-006` | spec |
| SPEC-59 | `解消済み-fnd-の元-forward-辺残存` | spec |
| SPEC-6 | `存在しない-id-への参照` | spec |
| SPEC-6-1 | `存在しない-id-参照を-rule-007-error-報告` | spec |
| SPEC-6-2 | `rule-007-は-always_error-で抑制不可` | spec |
| SPEC-60 | `fnd-resolved-状態の機械判定セマンティクス` | spec |
| SPEC-60-1 | `resolved-true-→-resolved-判定` | spec |
| SPEC-60-2 | `resolved-false-・未設定-→-unresolved-判定-省略時-false-既定` | spec |
| SPEC-60-3 | `resolved-が非-boolean-→-型不正として-rule-031-error` | spec |
| SPEC-61 | `対象-skill-の-llm-プロンプト資産を設計層-prompt-ノードで在グラフモデル化` | spec |
| SPEC-61-1 | `対象-skill-集合の各-skill-に対応する-prompt-ノードが在グラフに存在する` | spec |
| SPEC-61-2 | `各-skill-prompt-ノードが傘-spec-61-への依存辺を持つ` | spec |
| SPEC-61-3 | `各-skill-prompt-ノードがキャリア属性-skill｜agent-を持つ` | spec |
| SPEC-62 | `ノード本文に孤立-ノード分離記法の本文内誤用-が存在しない` | spec |
| SPEC-62-1 | `ノード本文中に孤立-行が存在しない` | spec |
| SPEC-62-2 | `本文中の孤立-を検出したとき-warning-を出力する` | spec |
| SPEC-7 | `孤立ノードの検出` | spec |
| SPEC-8 | `必須上流辺の欠如` | spec |
| SPEC-9 | `バージョンドリフトの検出` | spec |
| SPEC-9-1 | `依存辺のドリフト-→-rule-004-error` | spec |
| SPEC-9-2 | `義務辺のドリフト-→-決定の前提見直し` | spec |
| SR-1 | `著者が型・id・辺ルールを間違えずに書ける` | sr |
| SR-2 | `レビュアーが機械的に網羅性・整合性を検証できる` | sr |
| SR-3 | `メンテナが変更の影響範囲を辺でたどれる` | sr |
| SR-5 | `後工程の修正・指摘から影響する上流ノードを特定できる` | sr |
| SR-6 | `上流変更の下流への反映漏れ-ドリフト-を継続検出できる` | sr |
| SR-7 | `フェーズ・ステージ進行に応じて検査ノイズを制御できる` | sr |
| SR-8 | `レビュアー・メンテナがグラフを図として俯瞰できる` | sr |
| SR-9 | `仕様著者が既存図からノードを逆起こしできる` | sr |
| TERM-1 | `noderecord` | term |
| TERM-2 | `edgerecord` | term |
| TERM-3 | `violationrecord` | term |
| TERM-4 | `configslice` | term |
| TERM-5 | `coveragereport` | term |
| TERM-6 | `inspectionviews` | term |
| VAL-1 | `トレーサビリティ` | val |
| VAL-2 | `自動整合性検証` | val |
| VAL-3 | `著作効率` | val |
| VAL-4 | `段階的前進` | val |
| VAL-5 | `グラフの図的可視化` | val |
| VAL-6 | `図からの逆起こし-往復` | val |
| VERIFY-1 | `要件〜分析層の-spec-inspector-レビュー` | verify |
| VERIFY-2 | `n0-spec-品質強化分-再点検の実施記録` | verify |
| VERIFY-3 | `n5-p-単一責務点検-の実施記録` | verify |
| VERIFY-4 | `pr-#21-オーナーレビュー点検記録` | verify |
| VERIFY-5 | `requirements-層追加バッチ再点検記録-fnd-28-処置` | verify |
