# Issue 処理パイプライン（検証設計 → 解決設計 → テスト設計 → 実装 → 独立レビュー）

設計経緯や判断理由は [rationale](../../rationale/issue-pipeline.md)、障害・復旧手順は [troubleshooting](../../troubleshooting/issue-pipeline.md) を必要なときだけ参照する。

複数のオープン GitHub Issue を1件ずつ完結させる repo 運用オーケストレータ。主文脈は処置順の原案作成、オーナー判断の取り次ぎ、得られた決定の記録と実行、進捗管理を担い（**決めるのはオーナーであって主文脈ではない**——下記「役割分担」）、実装・レビューは利用可能な専用担当へ委譲する。

## 役割分担

- **主文脈＝オーナーとの対話窓口**：処置順の原案作成、オーナー判断を仰ぐこと、得られた決定の記録と実行を担う。**判断主体はオーナーであって主文脈ではない**——処置順の確定、先送り可否、スコープ拡張の起票要否、`scope` の覆し、`disposition` の決定はいずれもオーナーが決め、主文脈はそれを仰いだうえで取り込みレポートや台帳へ転記する担い手にすぎない（②-b・②-c）。
- **実装・レビュー担当＝非対話ファンアウト**：ユーザーへ直接質問せず、曖昧・矛盾・情報不足は STOP して原案＋比較＋理由付き推奨を返す。順序やオーナー判断を担当側で決めない。
- PF によって担当の権限境界と起動方式は異なる。機械ゲートがある PF はそれを使い、ない PF は wrapper に定める運用規律を守る。

## ① 処置順の原案 → オーナー承認

着手前に、主文脈はローカルの既定ブランチを `pull` で最新へ更新する。

1. オープン Issue の本文、依存（`depends on` / `blocked by`）、相互参照、同一ファイル群の競合を確認する。重い横断調査は read-only の調査担当へ委譲できるが、推奨順は主文脈が決める。
2. 各 Issue と Issue 集合の構成が妥当な単位に切られているかを、順序の検討とは独立に確認する。判定基準は `.ai/skills/gh-create-issue/SKILL.md` §3（材料は集約・軸1／軸2）・§4（成果は分割・`type:tracking` ＋ sub-issues への展開）を参照し、「材料（検討のインプット）」「成果（実行のアウトプット）」の概念を本 skill 側で再定義しない。次の2方向を**対称に**見る。
   - **分割漏れ**：1つの Issue が独立して完了判定できる複数の成果を抱えていないか。抱えているなら `type:tracking` ＋ sub-issues へ展開してから着手する。
   - **集約漏れ**：1つの設計判断に効く検討材料が複数の Issue に散っていないか。散っているなら検討を1箇所へ寄せてから着手する。
   検出しても Issue の分割・統合を自分で実行しない。`.ai/skills/gh-create-issue/SKILL.md` §1 の write 境界に従い、分割漏れ・集約漏れそれぞれについて、原案・比較・理由付き推奨を添えてオーナー判断を仰ぐ（PR7 の様式）。
3. 依存を有向グラフ化し、順序必須と並列可を分け、ブロッカーを先に置く。
4. 依存グラフ要約、推奨順、並列可否、リスク見立て、根拠、メリット／デメリットに加え、構成の妥当性の判定結果（分割漏れ・集約漏れの有無と、あれば是正の推奨）を提示してから、オーナーの承認または修正を得る。承認前に処置を始めない。

## ② 1 Issue を完結

前の Issue をオーナーが merge し、close を確認してから次へ進む。各 Issue は次の順序を崩さない。

### 作成工程（1a/1b/2a）

全Issueで以下の工程を別コンテキストへdispatchする。軽量経路は分析範囲の縮小に限り、
1a/1b/2aや独立レビューを省略する分岐を作らない。U-1/U-15は省略許可ではない。

| phase（機械値） | 担当 | 入力 | 成果物・次の独立レビュー |
|---|---|---|---|
| investigation | issue-investigator | Issue/snapshot/制約 | InvestigationReport。原因・挙動・影響・既存決定が一意でなければ必須 |
| verification_design | ac-designer | 調査報告または省略根拠 | VD（ST-TD/IT-TD/ST-TC/IT-TC）→ plan-reviewerによる単独レビュー |
| solution_planning | change-planner | 合格済みVD | CPとADR → 別dispatchのplan-reviewerによるVD↔CP整合レビュー |
| test_design | test-writer | owner承認済みCP/VDと単一work unit | UT-TD/UT-TC（Red実コード）→ pr-reviewerによる単独レビュー |
| implementation | issue-implementer | 合格済みTestDesign、plan ID/digest、単一work unit | Green化とdraft PR → 別dispatchのpr-reviewer |

主文脈はinvestigationの起動値と根拠を永続artifactへ記録する。著作者は自分のartifactを直接
commit/pushし、CP/VDをtmp handoffへ転載しない。作業完了receiptはartifact path/digestの短い参照に限る。
`python3 -m issue_envelope check --repo <root>` で木・DAG・schema・traceを確認し、
`issue_envelope.handoff.validate_handoff(data, expected)` で信頼callerのproducer/Issue/run/phase/
入力digest/OID/target/期待出力を照合する。期待値を入力artifactからコピーして通してはならない。
欠落・不一致・stale・STOP・未解消finding・未決owner decision・AC未対応は次phaseへ進めない。
各段の入力snapshotはその段のdispatch時点で固定し、前段成果物を後段で無断更新しない。

1a/1bのPlanReviewではACの機械判定可能性・曖昧さ・測定可能閾値・既存決定との矛盾を
項目ごとに検査する。1a単独→1b整合→ownerによるplan/split/decision承認の順を維持する。
2a合格後に2bが着手する。実装者は新規テストを著作せず、計画外判断なら上流へSTOPする。

1a/1b/2a/2bのreviewは同一Issueのkarteへ連番roundで取り込む。reviewerは書込/pushせず、
PlanReviewをcommitted envelopeにしない。capture本体は #375、karteの機械配線は #310、
将来run ledgerは #409 に委ねる。run/phase/dependency/expected outputの接続契約だけ保持し、
別ledgerを作らない。レビュー後の是正は既存②-c、ownerによるmergeは②-dを適用する。

### 作者間のbranch継承

`FBK-20261017-工程別worktreeへ同一branchを継承する` に従い、各作者は専用isolated worktreeを使う。
初回1aだけnew-branch、後続1b/2a/2bは前作者自身がcommit/pushした同branchのremote exact OIDをadoptする。
主文脈は前role完了receiptと終了・pushを確認し、既存collect/releaseで回収・解放を完了してから次roleを起動する。
回収receipt bytes、台帳の最新owner、Issue/branch/直前role、remote exact OIDを正規hookで照合する。
使用中worktree奪取や別branchでの迂回はしない。工程の独立レビュー・owner承認は引き続き必須。
PF固有markerと起動手順はClaude wrapperに従う。native有効化と新profileのlive実測は分けて記録する。

### 実行先、モデル、相談

Claude Codeが主文脈と工程roleを保持し、Codexは `codex_worktree_exec` の実行者として使う。
退役したCodex issue-pipeline/custom agentを復活させず、read-only roleへ書込profileを流用しない。
agyは #606/#628 とrole別実測が成立するまで無効とし、利用不能経路を成功扱いしない。
起動gate/profile/入力束縛はPF wrapperと `docs/methods/codex-workspace-binding.md` を適用する。
profileのorigin/main pinは変更せず、未merge profileの拒否を成功dispatchと報告しない。

read-onlyのCodex実行先は主文脈が事前に選ぶ。primaryからは
`python3 -m issue_start.readonly_workspace --source <primary絶対path> --approval-file tmp/<approval>.json`
へ通常のexecutor引数（`--role`、`-C <登録済みlinked絶対path>`、binding/prompt/output/model/effort）を渡す。
主文脈が既存の信頼済みlinked作業面を準備し、同一repo/HEADと入力bytesを検証したうえで、
専用入口が同じcwdからCodexを起動する。readonly自身にはprepare、cd、所有台帳、書込、pushを与えない。
新規worktree作成・trust設定・profile更新を自動化せず、D1の未merge profile拒否を維持する。

snapshot後のTD/TC/ADR/2b実装は、主文脈が承認済み差分を正確なrepo相対path→sha256で
binding.expected.source_changesへ渡す（commit済み削除だけnull）。過去の独立review receiptは
artifact digest/contextを凍結保持し、後段のsource変更はtrusted callerの進行承認として別に照合する。
globやdirectory一括許可を使わず、
承認外path・bytes差分・未commitの変更は拒否する。期待値を成果物から無条件生成して承認しない。


| ロール | 主要認知行為・Bloom | 層 / 予算 |
|---|---|---|
| issue-investigator | 分析 Lv4 | 中位 / 大 |
| ac-designer | 評価 Lv5 | 最上位 / 中 |
| change-planner | 創造 Lv6 | 最上位 / 大 |
| plan-reviewer | 評価 Lv5 | 最上位 / 中 |
| test-writer | 境界・反例の分析 Lv4 | 中位 / 中 |
| issue-implementer | 承認済み計画の適用 Lv3 | 中位 / 中 |
| pr-reviewer | 評価 Lv5 | 最上位 / 中、既存のrisk signalで引上げ |
| adviser | 相談内容の主要認知行為 | 上位 / 個別判定 |

具体ID/予算は `.ai/model-policy.json` と `model_policy/README.md` の既存resolverで解決し、
policy/catalog hash、取得surface/方法/日時、resolved ID、実使用ID、確認結果を追跡する。
共有資産・複数PF・権限/セキュリティ・fail-close・破壊的移行・永続状態・外部サービス・
複数work unit・曖昧AC・既存決定との矛盾・下流手順無効化の信号で層を引き上げる。
最上位を超える要求や必要層欠落はSTOPする。adviser利用を理由に元ロールを降格しない。

相談は構造化要求を主文脈が専用入口へ取り次ぎ、同じ担当roleへ返す。元role/run/phase/work unit、
artifact digest/OID、質問・試行、回数/時間/コスト予算へ束縛し、model/回答/採否/理由/検証を記録する。
新証拠なし、失敗、部分出力、予算到達は成功扱いせず主文脈へ返す。助言では必須レビュー、
STOP、karte escalate、権限拒否、owner承認を迂回できない。

### 3a/3bと運用検証

owner merge後の3aはST-TR/IT-TR/UT-TRを各TD/TCへつなぎ、3bは既存karte診断→fixer→再レビューを使う。
継続観測可能な異常は常設監視と #461 の報告経路、一度限りのlive確認は別verification Issueへ分離する。
実装Issueを実測待ちで滞留させず、実装のclose条件は必要な検証Issueとrelationの記録までとする。
別verification Issueを実装Issueのblocked-byにしない。判定値と根拠はCPへ記録する。

### ②-a 実装

- 実装担当を dispatch する前に、PF の Issue-start 契約（存在する場合）で Issue、repository、branch、base を再束縛する。契約エラーは別経路へ迂回せず fail-close する。
- Issue-start 契約が ALLOW を返した直後、実装担当を dispatch する前に、Project の `Status` を `In progress` にする。BLOCK なら着手せず `In progress` にもしない。`Blocked` を立てるのは同期ツール（`project_status_sync`）に委ねる。
- **`Status` の書き込みは主文脈が行い、実装担当には行わせない**。
- dispatch には Issue 番号、関連ノード、作業スコープなどタスク固有情報だけを渡す。恒常的な共有契約は各 PF の常設設定またはこの共通本文を参照させる。
- 戻り値は変更ファイル、テスト結果、PR（ある場合）、スコープ外指摘を含むハンドオフとする。STOP は主文脈が受けてオーナーへ打ち上げる。**戻り値の絶対パスが読めない場合は、main 作業ツリーの `tmp/_handoff/collected/` 配下の回収済みコピーを確認する**（詳細手順は各 PF の troubleshooting を参照）。
- **実装担当が STOP を返したら、`Status` を `Ready` へ戻してからオーナーへ打ち上げる**。

### 権限外操作の STOP と再開

追跡ファイルの削除・移動、`maintainability_lint baseline` による生成、生成結果の反映・手修正を含む baseline 更新は gated ロールに行わせない。実装・是正担当は対象パス、必要な理由、予定差分、検証方法をハンドオフに記録して STOP し、レビュー担当は必要性を同じ finding の列で報告する。別コマンドや編集ツールによる迂回も禁止する。

主文脈は報告をオーナーへ提示して実行確認を得る。確認済みの対象・差分だけを担当の対象ブランチで実行し、実行結果、実際の差分、検証結果を担当へ引き渡す。担当がその状態を確認してから再開する。確認を得られない場合は STOP を維持し、`check` の許可を baseline 更新の許可と解釈しない。

### ②-b 初回レビュー

- 初回レビューのモデル層／推論予算はリスク信号で選ぶ。共有資産、広域変更、前例のない判断、権限境界、曖昧な仕様があれば判断ボトルネックとして高い側を選び、根拠を1行残す。具体的な設定キーと写像は各 PF wrapper に置く。
- レビュー担当は各 finding の実害、根拠、期待値、再確認方法を構造化して返す。構造化 finding は `harm`/`harm_detail`/`severity`/`scope`/`locus`/`summary`/`evidence`/`expected`/`recheck`/`status` をキーとして返す。レビューコメントには AI 対応であることと具体的な変更・根拠を残す。
- **スコープ外の指摘も同じ finding の列に入れる**。別のセクション・チャットでの列挙へ逃がさない。スコープ内外は `scope: in | out` の申告として記録するだけで、`harm` の判定・記録台帳・clean 判定のいずれの免除にもならない。レビュー担当の `scope` は申告であって確定ではなく、これを覆せるのはオーナーだけである。
- **レビュー結果（初回・再レビューとも）を審査中の当該 PR へコメント投稿するのは、主文脈が毎回のオーナー確認なしに行う既定動作である。** 主文脈はレビュー担当から返った構造化 finding を当該 PR へ AI 帰属明記でコメントする。`.ai/guidance/common.md`「作業分離・判断境界」の実行前確認から除外するのはこの投稿だけとし、PR 本文の書き換え、別 PR・別 Issue・別リポジトリ・その他外部サービスへの投稿には実行前のチャット確認を要する。
- 承認・却下・clean を偽らない。未解消 finding があれば処置ループへ進む。

### ②-c 是正 → 再レビュー

- 是正は初回実装担当ではなく、レビュー指摘を受ける是正担当へ差し戻す。レビュー結果を先に記録し、是正担当は診断してから変更する。
- **レビュー結果を記録するとき、実装担当・是正担当のハンドオフに載った `out_of_scope_findings` も同じ finding の列へ写して記録する**。記録の実行は主文脈が行う（当事者ロールには行わせない）。
- **オーナーが決めた `disposition` と、オーナーが覆した `scope` は、主文脈が取り込みレポートへ書き足してから記録する。主文脈はこれらを決めない。** 手順は次のとおり。
  1. レビュー担当が返した finding レポートを受け取る（`disposition` は未記載）。
  2. `harm: real` の finding についてオーナーの処置方針（`fix-here` / `deferred` / `waived`）を仰ぐ。`deferred` なら行き先 Issue、`waived` なら許可者と理由もオーナーから得る。レビュー担当の `scope` 申告に疑義があるときも、**覆すかどうかは同じ場でオーナーに仰ぐ**（主文脈が独断で決めない）。
  3. 主文脈がその決定を、当該 finding のブロックへ `disposition:` とその付随キー（`deferred_to` / `waived_by` / `waived_reason`）として書き足す。**オーナーが `scope` を覆すと決めた場合**は `scope` の値も同じ場所で書き換える（書き換える手を動かすのは主文脈だが、覆すと決めるのはオーナーである）。
  4. 書き足したレポートを記録台帳へ取り込む（当事者ロールには取り込みを行わせない）。
- **決定は毎ラウンド再掲する。** 前ラウンドで未解消だった finding は全件再掲し、前ラウンドの `disposition` と、オーナーが覆した `scope` も書き写す。オーナーが方針を変えた場合だけ新しい値にする。
  - `disposition` の書き忘れは **fail-close 側**へ倒れ、未決定として clean を妨げる。
  - `scope` の書き忘れは **fail-open 側**へ倒れ、機械判定を止めずレビュー担当の申告値へ戻る。
- 再レビューは既定のレビュー設定で行う。ラウンド上限で打ち切らず、実害と無進捗を基準に続行・停止を判定する。
- **clean の条件は「未解消 finding が0件」ではなく「clean を妨げる未解消 finding が0件」**である（次節）。clean ならマージ経路へ進む。残る finding が実害なしだけでも握りつぶさず、起票案＋理由付き推奨を添えてオーナー判断を仰ぐ。

### ②-d オーナーによるマージ → クローズ

- review が clean になったら、主文脈は `rtk python3 -m pr_merge_gate report <PR番号> --repository <OWNER/REPO> --merge-method <merge|rebase|squash>` を実行し、fresh blocker report を確認する。report は同一snapshotを再読して安定性を確認するが、merge permit を発行せず、merge API を呼ばない。
- 主文脈は review 判定と report をオーナーへ提示して STOP する。merge はオーナーが GitHub UI 等から手動で行う。AI ロール・主文脈は merge／auto-merge を実行しない。
- report は取得時点の blocker evidence であり、オーナーの手動操作との間の状態変化を防がない。オーナーは結果を確認してから手動 merge を判断する。
- `Closes #N` で Issue が自動クローズされたことをオーナーの merge 後に確認する。閉じていない場合は次の Issue に進まず、主文脈がオーナーへ確認する。

## スコープ・先送り・矛盾

- 現 PR のスコープを超える対応は別 Issue に切り出し、現 PR に混ぜない。
- 先送り、繰り越し、対応不要は AI が独断で決めない。背景、検討結果、メリット／デメリット、推奨を示してオーナーの明示判断を得る。
- 既存決定と両立しない事実は勝手に解決しない。必要なら Q/FND 等の正式な記録を先に起票し、推奨を添えて停止する。

## 実害の定義とエスカレーション

`harm` は `real` または `none` とする。次のいずれかに該当する finding は `real` とする。

1. 仕様・設計との不一致、テスト退行、期待値の誤り。
2. fail-close、機械ゲート、検証、権限境界の迂回。
3. 正本・履歴・データの破損、契約違反、秘密・無認可コスト。
4. 後工程の誤読、名前と実体の不一致、トレーサビリティ断絶、正本の分岐、暗黙の前提、観測不能、再現性の欠如。

上記に該当しない純粋な語順・整形の好みや、根拠のない推測は `none` とする。迷ったら `real` 側に倒し、理由を `harm_detail` に書く。

**スコープ外（`scope: out`）は実害判定の免除ではない。** スコープ外と分類した指摘も `harm` を必ず付け、同じ finding の列へ記録する。

**実害ありの指摘には処置方針（`disposition`）の記録を要求する。** `harm: real` の finding は `scope` の値にかかわらず、次のいずれかが記録されるまで未処置とみなす。

- `fix-here` — 当該 PR で直す。直って `status: resolved` になるまで clean を妨げる。
- `deferred` — 別 Issue へ申し送る。**行き先の Issue（`deferred_to`）を必須**とする。
- `waived` — オーナーが明示的に処置不要を許可する。**許可者と理由（`waived_by` / `waived_reason`）を必須**とする。

**実害ありで処置方針が未決定の finding が1件でも残る間は clean にしない。** 判定は記録台帳の verdict に従う。`deferred` と `waived` は clean を妨げなくなるが、**`status` は `open` のまま残す**。

**この解除力は `harm: real` の finding にだけ与える。** `harm: none` の finding に `disposition` を書いても記録が残るだけで verdict は動かない。

次の場合は主文脈が STOP してオーナーへ打ち上げる。

- clean を妨げる未解消 finding が残り、それがすべて `harm: none` になった（記録台帳の verdict が `no-harm-only`）。`deferred` / `waived` と決めた `harm: real` の finding はこの判定対象から除外し、打ち上げるときはその finding と処置方針も併せて示す。
- `harm: real` の finding に処置方針（`fix-here` / `deferred` / `waived`）が未決定のまま残っている。処置方針の決定はオーナー判断であり、AI が単独で `waived` を選ばない。
- 記録台帳が無進捗と判定した（clean を妨げる同一 finding が3ラウンド連続で未解消）。**申し送り（`deferred`）／処置不要（`waived`）と決めた finding はこの計数から外れる**。判定は台帳側に置き、条文からこの条件を再実装しない。
- 診断・記録の類似飽和から転換しても解消できない。
- 是正担当が `status: stop`（矛盾・情報不足）を返した。

## karte 判定の報告分担

`karte ingest-review` / `karte close-attempt` の実行直後、実行環境が用意する通知機構が
`karte status --json` の判定を **AI の要約を経ずに** オーナーへ届ける契約とする。通知の
実装（発火経路・出力チャネル・検出対象コマンドの範囲）は PF 固有であり、各 PF の wrapper 側で
定める（Claude Code の実装は `.claude/skills/issue-pipeline/SKILL.md`「karte 判定の直接通知
（Claude Code 固有）」）。

- **主文脈はカルテの判定内容（verdict・未解消 finding・escalate 理由等）をチャットで再掲・要約しない。**
- **主文脈がチャットへ出すのは、判断に必要な選択肢と理由付き推奨に限る。**
- カルテの生の状態を確認する必要があるときは `python3 -m karte status --issue <N>` を実行する。手動実行では毎回全件を確認できる。
- 通知本文の内容（verdict の内訳・escalate の根拠等）は各 PF wrapper を参照する。

## 共通指示の配り方

恒常契約（決定点で前提・背景・メリット／デメリット・選択肢・推奨を添える、曖昧は STOP、スコープ外は起票提案）は PF の常設定義から適用する。dispatch prompt は毎回タスク固有情報だけにし、PF 専用の実行機構／権限／起動方式は各 wrapper に置く。重い調査の結果は素案であり、正本への無検証採用や確定著作に使わない。

## 初回レビューのリスク信号

レビューは Bloom Lv5 の評価とする。判断ボトルネック側の信号が1つでも強ければ大きい推論予算、すべて網羅性側なら既定の推論予算とする。

| 信号 | 既定の推論予算寄り（網羅性） | 大きい推論予算寄り（判断） |
|---|---|---|
| ブラストレディアス | 局所（1〜数ファイル） | 共有資産・コーパス横断・多数の参照伝搬 |
| 変更規模 | 小・定型追加 | 構造改変・広域リファクタ |
| パターンの新規性 | 既存パターン踏襲 | 前例なし・新規構造・設計判断 |
| 対象の性質 | プローズ・資産テキスト | 権限境界・グラフ構造・型 |
| 可逆性 | 容易に差し戻せる | 不可逆・広範囲に波及 |
| 仕様の明確さ | 受入基準が一意 | 曖昧・利害 trade-off・解釈の余地 |

迷ったら大きい推論予算側に倒し、選定根拠を1行残す。レート制限やセッション上限を理由に降格しない。再レビューは既定の推論予算とし、初回のリスク信号で降格しない。

## done

- 推奨順を依存グラフ＋根拠付きで提示し、構成の妥当性（分割漏れ・集約漏れ）の判定結果も添えて、オーナー承認を得ている。
- 各 Issue が implement→PR→review→owner report→オーナーによる手動 merge→close を1件ずつ完結している。
- 初回レビューのモデル層／推論予算と根拠、レビュー finding、是正・再レビュー結果が記録されている。
- スコープ外対応は別 Issue、先送り・据え置きはオーナー明示判断になっている。
- スコープ外の指摘も finding として同じ列に記録され、実害ありの指摘は処置方針（`fix-here` / `deferred` / `waived`）が決まってから owner report を作成している。
- 主文脈は実装・レビューを代行せず、タスク管理・進捗報告と、オーナー判断の取り次ぎ・記録を担っている（意思決定の主体はオーナーであって主文脈ではない）。
