# ダッシュボード

議事録から抽出した未決事項とネクストアクションの運用ハブ。
新しい議論が出たら、ここを更新する。

最終更新：2026-06-06（Q17 確定→[13](requirements/13-stabilization.md)／Q5a 文法明文化→[schema](schema/README.md)／S1–S4 要件化／データ辞書＋クラス設計を [design/](design/00-data-dictionary.md) に追加）

## 🎯 MVP ターゲット（確定）

**MVP ＝ [12-mvp-scope](requirements/12-mvp-scope.md) の P1 ＋ P2。**

- **P1 コア（不可分A）**：受付 → 基準合成(org) → AI評価 → 検証・仕分け → レポート（＋未分類）。
  ＝「文書を出すと、観点に沿った指摘が 🤖/✋/💬/❓ に仕分けられたレポートが返る」。
- **P2 差別化**：✋/💬 人手適用 →（不可分B）🤖 自動修正＋revert。
  ＝「直してくれて、いつでも戻せる」。
- **前提（P0）**：観点ファイル＋ポリシーを書く（少数 doc_type）／決定的ツール群＋プロンプト雛形（Claude が LLM 役）。
- **MVP 外**：合成時警告(F11)・育成ループ(F12/13)・AI型推定(F15)・参照突き合わせ(F10)・異常系(F16)・team/project scope(F17)。

> 開発着手の前に、ここまでの設計プロセスを**資産化**（スキル/エージェント化）する → [methods/](methods/method-inventory.md)。

## 🔨 実装進捗（MVP・TDD）— レート制限時の再開ポイント

> 各層 commit→テスト→成績書(commit id)→push。証跡は `tests/{cases,reports,logs}`。再開時はこの表の最初の ⬜ から。

| # | 層/モジュール | 内容 | 状態 |
|---|---|---|---|
| 1 | `domain`（基盤） | enums・result・ids・review・intake | ✅ TC-domain-001（22） |
| 2 | `parsing` | 自前 mini-YAML パーサ＝S5 lint | ✅ TC-parsing-001（19） |
| 3 | `domain/criteria`＋policy 型 | RuleMeta/ComposedRule/CriteriaPack/MetaIndex/PolicyMatrix/TriagedFinding 等 | ✅ |
| 4 | `ports` | PlatformPort（Protocol）。Repository は persistence 直実装で代替 | ✅ |
| 5 | `core/triage`（P4） | rule_id検証(S1)→参照除外→mode判定／未宣言は HUMAN_ONLY(S2) | ✅ TC-triage-001（11） |
| 6 | `core/compose`（P2・org最小） | org 読込→pack/meta 組立（方向ゲート/矛盾は post-MVP印） | ✅ TC-compose-001（4・純粋部） |
| 7 | `core/intake`（P1） | 対象/参照集合・型確定（org固定・手動型・AI推定は MVP外） | ✅ TC-intake-001（1・純粋部） |
| 8 | `ports`＋`adapters/fake` | PlatformPort/能力宣言＋FakePlatformAdapter（テスト seam） | ✅ |
| 9 | `core/evaluate`（P3）＋`core/pipeline`（P1通し） | PF呼び→検証→仕分け→レポート＋版スタンプ。fail-close 直列 | ✅ TC-pipeline-001（6・e2e） |
| 10 | `persistence`（criteria/policy ローダ） | parser拡張(Q24=A)＋criteria_repo（.md→ComposedRule・policy→PolicyMatrix）。git/ledgers は P2 で | ✅ TC-repo-001（4）／TC-parsing +2 |
| 11 | `core/apply`（P5）＋report＋CLI配線 | HTMLレポート＋内部git適用(S4)＋revert＋feedback(DS5)。`review`/`revert`/`feedback` は **レポートのパスだけ**(DD10/14)。実PF=FilePlatform(findings.json) | ✅ TC-cli-002（4） |
| 12 | `io/cli`（合成ルート） | `reviewer version`（版定数表示）・`review`→HTML。`python -m review_system` 実起動可 | ✅ TC-cli-001 |
| 13 | e2e（CLI・FakePlatform） | `python -m review_system review …`→HTML 実生成。version も実行可 | ✅ TC-cli-001（4） |

> **MVP外（実装しない・PR8 印）**：合成時警告(F11)・育成ループ(F12/13)・AI型推定(F15)・参照突き合わせ(F10)・異常系degrade(F16)・team/project scope(F17)。


## 🔥 ネクストアクション（次にやる候補）

| # | アクション | 目的 | 状態 |
|---|---|---|---|
| A1 | 評価基準ファイルのスキーマを実際に書く | サンプルで曖昧さを潰す | 🟡 叩き台あり（[schema/](schema/README.md)）→レビュー待ち |
| A2 | AI への入力設計を決める | 基準＋文書をどう渡すか / 長い文書・コードベースの扱い | 🟡 設計あり（[07](requirements/07-ai-input-design.md)）→レビュー待ち |
| A3 | MVP の線引き | **確定：MVP＝P1＋P2**（[12-mvp-scope](requirements/12-mvp-scope.md)）。方向性：決定的ツール群（MCP）＋プロンプト雛形を作り、Claude が LLM 役で回す（[11](requirements/11-platform-adapter.md)） | 🟢 確定 |
| A4 | これまでの設計プロセスを資産化 | 案出し・イベントリスト・点検・価値分析などの手順/基準をスキル・エージェント化（[methods/](methods/method-inventory.md)） | 🟡 棚卸し済→構築計画あり |
| A5 | **実装前の凍結セット（8項目）を固める** | A モジュール構成・②外部IF・B PF駆動プロトコル・C 永続層・①オーケストレーション(スイムレーン)・③システムプロンプト・D ログ/版・④テスト戦略。索引＝[design/README](design/README.md)。判断ログ＝[design/decisions](design/decisions.md) | ✅ 8項目確定（DD1–DD12 暫定決定・spec-inspector G1–G8 反映）→ 実装フェーズへ |

## ❓ 未決事項（決めないと進めない論点）

| # | 論点 | メモ | 状態 |
|---|---|---|---|
| Q1 | 基準変更は誰がやってよいか | 個々の上書きの可否は override で**機械判定（承認ステップ無し）**。人間の確認が要るのは「基準ファイル自体を編集・確定する行為」だけ。**MVP はアクターを区別しない**（単一ユーザー・人間確認まで）、ロール強制（RBAC）は将来。Git ホスト権限には乗せない | 🟢 MVP 方針確定（強制は将来） |
| Q2 | determinism の判定をどう運用に乗せるか | **クローズ**：determinism は基準作者が**フロントマターで宣言する属性**（[schema](schema/README.md)）で、⑥仕分けが決定的に消費（`rule_id→determinism×severity→モード`）。別途の運用機構は不要＝2軸どおり（順序属性＝機械ゲート）。生成側の主体は Q21。安全側デフォルトは S2（未宣言は人間側へ） | 🟢 クローズ（schema/2軸に吸収） |
| Q3 | 自動修正サマリの粒度・revert 単位 | **revert 単位＝指摘(finding)単位でコミット**（finding id＝rule_id＋location）。個別 revert も実行ぶん一括も、対象コミット群の revert で成立（一括は操作）。実装：内部に一時ローカル git（外部ホスト依存とは別物） | 🟢 方針確定 |
| Q4 | 文書タイプの判定 | **AI 自動判定を既定＋手動上書き**。低確信時は手動を促す。誤判定＝誤基準なので上書きを常に効かせる（[08](requirements/08-intake-design.md)） | 🟢 確定 |
| Q5 | 技術スタック | **確定：アプリ本体＝Python・原則標準ライブラリのみ**（外部依存は最小）。AI レイヤは外部 PF へ委譲済み（[11](requirements/11-platform-adapter.md)）。git は `subprocess` で CLI 呼び。**Q5a 確定＝自前の最小フロントマターパーサ**（stdlib のみ・PyYAML 不採用）：対応文法を**意図的に小さく固定**（フラット key:value＋単純リスト＋override の1段ネスト）し、**範囲外は S5 lint で fail-close**。**パーサが検証器(S5)を兼ねる**。要：対応文法を [schema](schema/README.md) に明文化 | 🟢 確定（Q5a＝自前パーサ） |
| Q22 | PF 能力差の吸収 | 当面はファイル適用・ツール実行の2能力をシステム代替できれば十分（気にしすぎない）。別途、**自前実装の方がコントロールしやすい範囲が無いかを調査**＝[11](requirements/11-platform-adapter.md) に build-vs-delegate のたたき台 | 🟡 当面OK／要調査 |
| Q23 | 双方向の口の境界・順序ガード | PF→System の実装は **CLI＋stdout でシステムが制御フローを流し順序を握る**（起動プロンプトは「起動方法＋入力＋指示に従え」の最小）。どの関数を公開するか・適用前検証の強制は本番でツール側ガード。MVP は stdout 指示で軽量に担保（[11](requirements/11-platform-adapter.md)） | 🟡 MVP方針あり |
| **Q24** | **ポリシー記法 ↔ パーサ非対応（矛盾）** | [schema](schema/README.md) の policy 例が**フロー `{ "*": mode }`＋`*` キー**で、Q5a の mini-YAML サブセット（フロー/`*`/3段ネスト非対応）で**読めない**。実装で発覚。原案＝**(B) policy を `determinism: mode` のブロック平坦形に再設計**（MVP の `PolicyMatrix` は既に determinism→mode で severity 不使用＝損失なし／パーサ拡張不要）。代替＝(A) パーサ拡張（引用キー＋3段ブロック・Q5a を広げる）。**推奨 B**。要オーナー判断 | 🟢 **決定=A（パーサ拡張）**：引用キー("*")＋3段ブロックネストを mini-YAML に追加（flow は非対応のまま）。schema の policy 例はブロック形に書き換え。DD16 | 
| Q6 | 無効化の責務の二重化 | 事実(基準)と好み(ポリシー)を混ぜない＋方向ゲート制で整理。緩めはポリシー/承認経由、完全オフは `enabled` に一本化 | 🟢 方針合意（明文化済み） |
| Q7 | LLM の id 誤付与のフォールバック | **第4区分「❓ 未分類」として surfacing**。自動仕分けせず、人の確認＋新ルール候補（育成）へ。未分類化は2経路＝(a)LLM自己申告 (b)**rule_id がパックに無いものをプログラムが検証して回送**（[09](requirements/09-processing-pipeline.md)⑤） | 🟢 確定 |
| Q8 | `category` の語彙 | **enum 強制はしない（テキスト編集できる以上、非現実的）**。自由記述＋**推奨語彙（ソフト規約）**で運用、集計は存在する文字列でグループ化。AI クラスタリングによる正規化提案は MVP 不要＝将来の育成機能候補（[schema](schema/README.md)） | 🟢 確定（ソフト規約） |
| Q9 | 承認者への打ち上げ＋**警告の既出判定** | 機構(設計)＝(a)方向検出の結果を人へ surfacing (b)**警告レジャー：`hash(対象ルールのメタ+本文)` で既出判定し、既出は再警告せずレポートに「既知」として混ぜるだけ**（完全に機械的。[schema](schema/README.md#警告の既出判定warning-ledger)）。cadence/しきい値等は運用デフォルト | 🟢 機構=設計確定 / 規則=運用 |
| Q10 | 同一 `doc_type×scope` の複数ファイル結合規約 | スコープ内は**対等な兄弟・順序なし**（順序での暗黙解決はしない）。各ルールに provenance（由来パス）を保持。同 id 衝突は「メタ＝決定的に同値判定／本文＝LLM が**矛盾の有無だけ**判定」し、**矛盾なし→共存・矛盾あり→親フォールバック＋警告**。LLM は方向ではなく整合性判定に使う（2軸原則を維持）。警告は人へ（Q9接続） | 🟢 方針合意（schema 明文化済み） |
| Q11 | `override`（特に `locked`）を宣言できるのは誰か | **クローズ（MVP 非該当）**：機構（3値 `locked/tighten-only/open`＋方向ゲート＋合成時の機械判定）は確定済み。**「誰が宣言してよいか」の強制は将来の RBAC**（Q1 と同バケツ）。MVP は **org 固定スコープ**（Q13）で多段継承が無く論点が発生しない。**F17（team/project 3段継承）着手時に Q1 と一体で再起票** | 🟢 クローズ（Q1/F17 へ統合） |
| Q12 | 文書の入力粒度 | **関連ファイルをまとめて1レビュー**（バッチ単位・横断整合も見る）。アップロード基本（[08](requirements/08-intake-design.md)）。※回答中に I-13 参照コンテキストの欠落が発覚 | 🟢 確定 |
| Q13 | スコープの決定方法 | **scope の定義は観点ファイルのフロントマター**（`scope`/`extends`）＝I-4 の中身で別 config/状態にしない（旧 I-11 削除）。**MVP は org 固定**、per-review の選択は I-3（任意）。team/project は MVP 後（[08](requirements/08-intake-design.md) / [schema](schema/README.md)） | 🟢 確定（MVP） |
| Q14 | ~~同一文書の再評価時の挙動~~ | **クローズ：区別しない**。システムはステートレスに、渡されたものを淡々とレビュー＝再提出は単に再レビュー。区別には記憶が要り無駄。修正漏れは普通に起きる前提。※"警告"の dedup は別物で Q9 のレジャーで対応（指摘は毎回出す／警告は一度で足りる、と状態の要否が逆） | 🟢 クローズ |
| Q15 | 基準/ポリシー更新の伝播 | **クローズ**。変更検知トリガは持たない（テキスト編集・非Git前提で検知困難）。①合成はレビュー実行のたび毎回（決定的・AI不使用で安価）②本文矛盾チェック(LLM)だけ `content_hash` でキャッシュ照合・不一致で再実行（矛盾検知/警告レジャーと同機構）③過去文書への**遡及はしない**（新基準は以後／再提出で適用＝Q14と同じ） | 🟢 クローズ |
| ~~Q16~~ | ~~承認待ち滞留への督促~~ | **クローズ（削除）**：承認待ちが片付いたかを**システムは観測できない**（レビューはステートレス・対応は系外）。通知後の顛末を追えず督促の前提が無い。E13/O-13 削除 | 🟢 クローズ（不要） |
| Q17 | 異常系イベントの振る舞い | **確定**（下「🧯 異常系の方針」）：原則 **「疑わしきは fail-close＋明示エラー(O-14)／空文書だけ benign no-op」**。⑦自動適用は**クリーンな F4 が前提**＝失敗時は書込なし。**全段 fail-close＋O-14 明示は MVP に含む**、per-unit graceful degrade のみ F16(post-MVP)。要件＝[13-stabilization](requirements/13-stabilization.md) S3。S3/S5 と一体 | 🟢 確定 |
| Q18 | 観点パックの肥大化対策 | **MVP は全部載せ**（doc_type で絞り済み）。膨張時の retrieval 的選別は MVP 後の最適化（[07](requirements/07-ai-input-design.md)） | 🟢 確定（MVP） |
| Q19 | 参照コンテキストの紐付け | Q12 回答で発覚（I-13）。上流成果物・前提条件を評価対象と別枠で入力。**MVP は手動添付・任意・複数可**。どの観点がどの参照を要求するか等の自動紐付けは将来（[08](requirements/08-intake-design.md)） | 🟡 MVP方針あり |
| Q20 | 同一実行内の自動修正衝突 | **2段構えで確定**：①LLM がマージ案を生成 ②「迷い」は人が決定。LLM の返り値に迷いフラグを持たせ、システムが人へルーティング（[10](requirements/10-llm-system-boundary.md) L4）。finding 単位コミット(Q3)とセット | 🟢 方針確定 |
| Q21 | 決定論的な修正の生成主体 | **確定：ツール化しやすいところはツール化**。整形/import整列/lint自動修正/誤字/ケース変換は決定的ツールが生成、判断含むものは LLM。候補一覧は[10](requirements/10-llm-system-boundary.md) | 🟢 確定 |

## 🧯 異常系の方針（Q17 確定）

> ✅ 承認済み（2026-06-06）。要件は [13-stabilization](requirements/13-stabilization.md) S3 に落とし込み済み。

原則：**価値経路は遮断しないが、誤った結果は出さない。疑わしきは fail-close＋明示エラー（O-14）。
fail-open は「続けてもリスクが無い良性ケース」に限る（＝空文書）。**
自動適用⑦は**完全・クリーンな仕分け(F4)が前提**で、上流失敗時は一切書き込まない（半端を残さない＝ステートレス）。

| 異常(E14) | 段 | MVP の振る舞い | 根拠 | post-MVP(F16) |
|---|---|---|---|---|
| 基準パース失敗 | ②合成 | **fail-close**：レビュー中止＋O-14（どのファイル/なぜ）。org 少数ファイルなので全体停止で安全 | 黙って落とすと「網羅した」と誤認＝偽の安心 | 当該ファイルのみ skip＋「N/M 適用」明示の degrade |
| LLM 障害（PF 到達不可/タイムアウト） | ④評価 | **bounded retry→fail-close**：findings 無し＝価値無し。**⑦自動適用は走らせない**。O-14 明示 | 中核(F3)。捏造・部分適用は事故 | バッチ単位で部分 degrade（独立呼出時） |
| LLM 出力が不正（schema 違反/偽 rule_id） | ⑤検証 | **degrade（既設計）**：不正 finding は ❓未分類へ。crash/silent-drop 禁止 | 受け口を固く（S1）。rule_id 検証は既設 | 同左（強化） |
| スコープ未解決（doc_type 不明/`extends` 切れ/基準ゼロ） | ①② | **fail-close＋実行可能エラー**：「doc_type=X の基準が無い／extends 先が無い」。空の既定にフォールバックしない | 黙って薄い評価＝偽の安心 | 切れた継承リンクを名指しで surfacing |
| 空文書（評価対象が実質ゼロ） | ①intake | **fail-open（良性 no-op）**：0件レポート「評価対象なし」。エラーにしない | 続けてもリスク無し＝遮断しない(PR6) | 同左 |

## 🛡 価値実現の安定化（洗い出し：S1–S6＝MVP／S7–S9＝post-MVP）

P1（出すと仕分けレポートが返る）・P2（直す＋戻せる）を**安定して**届けるための具体物。
最大の不安定要因は**唯一の非決定ステップ＝LLM(④)**。ここを固く・失敗を可視化・書込を安全側に倒すのが要。

> ✅ **S1–S4（MVP 必須）は [13-stabilization](requirements/13-stabilization.md) で要件化済み**（S5/S6 も同書に MVP 推奨として記載）。

| S# | 安定化策 | 何を防ぐ | 関連 | 段階 |
|---|---|---|---|---|
| S1 | **LLM 出力の契約検証を固く**（⑤）：strict schema→非適合は ❓未分類。crash/silent-drop 禁止 | 幻覚 id・欠損 location・壊れ JSON での事故/取りこぼし | Q7,⑤ | **MVP 必須** |
| S2 | **仕分けの安全側デフォルト**：determinism 未宣言/不明は**人間側(✋/💬)**へ、🤖 にしない | 誤宣言由来の誤自動適用 | Q2,⑥ | **MVP 必須** |
| S3 | **異常系ポリシー(Q17)**：疑わしきは fail-close＋O-14／空文書のみ no-op／⑦はクリーン F4 前提 | 部分結果での誤適用・偽の安心 | Q17 | **MVP 必須** |
| S4 | **自動適用のトランザクション性**：失敗時は書込ゼロ／finding 単位コミットで常に revert 可 | 半端な書き換えが残る | Q3,F6/F8 | **MVP 必須** |
| S5 | **基準の事前 lint**（実行前検証）：frontmatter 妥当・override∈{locked,tighten-only,open}・extends 存在 | E14 を実行時でなく**作成時**に倒す | Q17,schema | **MVP 推奨** |
| S6 | **結果の provenance/版スタンプ**：PF/モデル＋プロンプト雛形版＋基準 content_hash をレポートに記録 | 「なぜこの結果か」が説明不能・再現困難 | Q15,07 | **MVP 推奨** |
| S7 | per-unit graceful degrade（F16 本体） | 1ファイル障害で全体停止 | Q17,F16 | post-MVP |
| S8 | 過大入力の検出/分割（無言の truncation 禁止） | 長文/肥大パックでの無言の劣化 | Q18,07 | post-MVP |
| S9 | 合成出力の正準順序（union を sorted＋provenance 固定） | プロンプト揺れ由来の出力不安定 | Q10,② | post-MVP |

## 🗂 未決の分類と優先度

**区分**で「設計（＝システムが出す機構）」と「運用ルール（＝システムが前提とする条件・組織が設定するデフォルト）」を分ける。
**運用ルールは設計で詰めない**——機構だけ設計し、規則はデフォルト/前提として置く（2軸の運用側）。

| テーマ | Q# | 区分 | 優先 | メモ |
|---|---|---|---|---|
| 入力境界（文書→システム） | Q4 / Q12 / Q13 / Q19 | 設計（IF） | **高** | 🟢 確定（[08](requirements/08-intake-design.md)）。参照コンテキスト I-13 は MVP方針あり |
| LLM 出力の受け口 | Q7 / Q18 | 設計 | **高** | 🟢 確定（[07](requirements/07-ai-input-design.md)）。未分類=第4区分・観点パック全部載せ |
| 自動修正の機構 | Q3 / Q20 / Q21 | 設計（機構） | 中 | revert＝finding単位コミット／衝突解決=2段構え(Q20)／決定論的修正の生成主体(Q21) |
| 基準スキーマ細部 | Q8 | 設計 | 中 | category 語彙＝集計の厳密化 |
| 基準の上書き権限 | ~~Q11~~ | 運用ルール | — | 🟢 クローズ（MVP=org固定で非該当・F17/Q1 へ） |
| 承認・ガバナンス | Q1 / Q9 | 運用ルール | 中 | **機構のみ設計**、規則は組織のデフォルト。詰めない（Q2 はクローズ＝schema 吸収） |
| **価値実現の安定化** | **S1–S6** | **設計** | **高** | LLM 受け口(S1)・安全側仕分け(S2)・異常系(S3)・トランザクション(S4)。MVP 必須 → [13-stabilization](requirements/13-stabilization.md) で要件化 |
| ライフサイクル機構 / 異常系 | Q17 | 設計 | 中 | 🟢 確定（fail-close＋O-14／空文書 no-op）。[13](requirements/13-stabilization.md) S3。S3/S5 と一体 |
| ~~滞留督促~~ | ~~Q16~~ | — | — | 🗑 削除（滞留はシステムが観測不能） |
| 実装 | Q5 | 設計 | 中 | 🟢 Python・原則 stdlib のみ。**Q5a＝自前の最小フロントマターパーサ**（検証器 S5 を兼ねる・対応文法を schema に明文化） |
| 合意済み（参照） | Q6 / Q10 | 設計 | — | 確定・明文化済み |

> 進め方の指針：**高（Q4/Q12/Q13/Q7/Q18 ＋ 安定化 S1–S6）は全部「設計」**。実装前に S1–S4 を仕様へ落とす。
> **運用ルール（Q1/Q9）は機構＋デフォルトに留め、設計で詰めない。**（Q2＝schema 吸収・Q11＝F17/Q1 へ・Q16＝観測不能で削除）

## ✅ 決定済み（参照用）

- 社内ツールとして作る
- 評価基準は構造化 Markdown で外部ファイル化、Git 管理
- `文書タイプ × スコープ` で動的選択・継承
- 指摘は `深刻度 × 対応モード` で自動仕分け
- 自動化レベルはコンフィグ可能（決定論的＝ログのみ 〜 判断要＝人間）
- Human-only でも AI が原案提示
- auto-fix は自動修正サマリで可視化＋一括 revert
- 流し読みのフィードバックが基準・ポリシー育成に直結
- **設計（機構）と運用ルール（前提条件）を混ぜない**：設計は機構を出す（方向の検出・器・provenance・revert・AI I/O）。運用ルール（誰が承認・緩めの承認要否・督促頻度）は機構上のデフォルト/前提として置くだけで設計では詰めない（2軸の運用側）
- 上書きの**方向ゲート（org 権威）**：追加・厳しく=自由 / 緩め・無効化=**既定で機械拒否**（org が `open` したルールのみ可）/ `locked`=不可。完全に機械判定で**承認ステップ無し**。override の3値は `locked | tighten-only(既定) | open`
- 判定は常に**2軸で分ける**：システムの判定基準（順序ある属性=機械が自動ゲート）／運用ルール（本文・事実性=人が確認）
- 本文（観点）の上書き＝差し替え扱い（open のみ可・他は機械拒否・locked 不可）。観点/例の追加は別ファイルで union
- **MVP はアクターを区別しない**（単一ユーザー）。専用 RBAC も Git ホスト権限依存も採らない。役割ラベルは記述的。方向ゲートは「検出」まで機能し、「誰が承認するか」の強制は将来
- **LLM は自前実装せず外部 PF（Claude Code/Copilot 等）に委譲**。システムは PF のラッパーで、接続部は**アダプタパターン**（PF 差し替え可・自前実装も同じ口に差せる）。出力はアダプタ越しでもシステムが検証する（[11](requirements/11-platform-adapter.md)）
- **口は双方向**：System→PF（ヘッドレス）と PF→System（決定的処理を function calling / MCP ツールで公開）。同じポートを両向きから使う。**MVP は「ツール群＋プロンプト雛形」だけ作り、Claude が LLM 役を担って高速に検証**（オーケストレータ/UI は後）。ツールは後で System 駆動に切り替えても再利用（[11](requirements/11-platform-adapter.md)）
- **実装前の凍結セット（8項目）**を固めてから着手：A モジュール構成・②外部IF・B PF駆動プロトコル・C 永続層・①オーケストレーション(スイムレーン付フローチャート)・③システムプロンプト・D ログ/版・④テスト戦略。索引＝[design/README](design/README.md)
- **モジュール構成はヘキサゴナル＋依存内向き**：`domain ← core(ports) ← adapters/persistence/cli`。コアは PF/IO/保存形式を知らず、結線は合成ルート(`io/cli`)のみ（[design/02](design/02-module-architecture.md)）
- **テスト戦略**：unittest（全 public 関数）／ケース＝Markdown／成績書＝ケースコピー＋実測＋commit id／ログ＝stdout ダンプ／失敗も残す（隠蔽禁止＋原因/対策）／テスト前コミット／e2e は Claude Code エージェントで同じ3点セット。非決定（LLM）は `FakePlatformAdapter` で決定化＝アダプタ境界＝テスト境界
- **資産のテーラリング運用（A16）**：プロセスはスキルで実現するためテーラリング実体は `.claude/`（docs でない）。汎用標準＝`.claude/standards/`（非活性）、テーラリング済 active＝`.claude/skills/`、対応台帳＝`.claude/tailoring-registry.md`。テーラリング時は元を `git mv` で非活性化（消さない）し registry に記録。本PJは extract-then-generalize。初回適用＝`/test-strategy`

> 各決定の詳細は [requirements/](requirements/) を参照。プロセス設計（DFD/状態）は [process/](process/00-context.md)。
> システムの入出力一覧は [requirements/05-io-overview.md](requirements/05-io-overview.md)、
> イベント駆動の俯瞰は [requirements/06-event-list.md](requirements/06-event-list.md)。
> **実装設計**：データディクショナリ集約は [design/00-data-dictionary.md](design/00-data-dictionary.md)、
> 型安全なドメインモデル（dataclass）は [design/01-class-design.md](design/01-class-design.md)。
