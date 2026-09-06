# GitHub Issue を作成する

すべての説明・質問・報告を日本語で行う。1 Issue を1つの検証可能な成果に保ち、実環境から取得した分類体系へ整合させる。

## 1. 実行境界を確定する

1. 「Issue を作成して」「起票して」など、GitHub への書き込み依頼が明示されているか確認する。明示されていなければ調査と draft の提示だけを行い、Issue、Project、relation を変更しない。
2. 対象 repository を remote、会話、GitHub 情報から特定する。推測だけで別 repository を選ばない。
3. repository の適用規約と、そこから参照される Issue 運用規約を読む。AI attribution、言語、権限、スコープ、先送りに関する規約を優先する。
4. 利用可能な GitHub tool で repository、Issue、label、Project を読み書きできるか確認し、不足する機能だけ CLI で補う。権限不足、対象不明、規約矛盾なら fail-close で停止し、対話的な確認手段で必要な判断または権限をユーザーへ具体的に求める。

Issue 作成の明示依頼は、別 repository、追加 Issue、先送り、課金、または既存 Issue の破壊的変更への包括許可ではない。

## 2. live metadata を取得する

作成前に毎回、対象 repository の全 label と、対象 repository に紐づく GitHub Project 候補を実環境から取得する。ユーザーが Project を明示していなければ、候補が1件の時だけ選択する。0件または複数件なら候補と推奨を提示して、Issue または Project への write 前に停止する。ユーザーが Project を明示した場合も、その Project が対象 repository を扱うことを確認する。draft-only では候補を提示するだけで選択・変更しない。

選択した Project の fields/options、`viewerCanUpdate` 相当の update 権限、Issue を同 Project へ手動追加する権限と手段を live で確認する。いずれかを確認できなければ write 前に停止する。Auto-add は公開APIから取得できる workflow の名前と enabled 状態だけを参考情報として確認する。repository/filter の適用条件詳細は公開APIから検証できないため、確認不能を停止条件にしない。label 名、Project number、field ID、option ID、repository ID、Issue ID を記憶や本文例からハードコードしない。

最低限、次を取得して名前とIDを対応付ける。

- labels: `area:*`、`type:*`、`concern:*`
- Project fields: `Status`、`Workstream`、`Priority`、`Horizon`、`Review date`、`Harness`
- relation 候補: parent、sub-issues、blocked-by/blocking

期待する名前が live metadata にない、表記が異なる、同義候補が複数ある場合は勝手に label/option を作らず停止する。差分と推奨案を示し、対話的な確認手段でユーザー判断を得る。

## 3. open/closed の重複を調べる

open と closed の両方を検索する。タイトルの語句一致だけで判断せず、次を比較する。

- 対象 path、module、Project root
- 症状と root cause
- 目的と acceptance criteria
- parent、sub-issues、related Issue

起票先の判断は**2つの軸**で行う。両軸は独立しており、どちらか一方だけで結論を出さない。

判断に入る前に、Issue が2つの別物を運んでいることを踏まえる。**材料**（その対策を設計するために卓へ載せる検討のインプット）と、**成果**（完了を客観的に検証できる実行のアウトプット）である。両軸が決めるのは**新しく見つけた事実をどの Issue に載せるか**、すなわち材料の置き場であり、実行単位をいくつにするかは §4 が決める。材料を集約することと成果を分割することは両立する。

### 軸1：root cause の同一性

同じ成果または root cause を扱う Issue があれば、新規作成を止める。既存 Issue への追記、reopen、sub-issue 化、または別 Issue が妥当かを根拠付きで提案し、ユーザーが新規作成を改めて選んだ場合だけ続行する。

### 軸2：対策検討時の検討材料になるか

root cause が異なっていても、対策は原因ごとではなく**対象（ロール・機構・モジュール）ごと**に設計される。そのため、**次の両方を満たす**既存 Issue があれば、新規に Issue を立てるのではなく、その Issue へ材料として載せることを検討する。

- 対策の選択肢が重なる、または一方の対策選択が他方の設計判断に直接影響する（例：同じロールへ権限を追加する対策を採ると、その権限が及ぶ範囲の是非も同時に決まる）。
- 一方を見ずに他方だけを見て対策を決めると、部分最適な対策になる具体的な経路がある。

軸2 が決めるのは材料の置き場だけである。材料を1つの Issue へ載せたことは、実行を1つにする理由にならない。**集約した材料から複数の成果が出るなら、実行単位は §4 に従って分割し、`type:tracking` ＋ sub-issues へ展開する。**

**歯止め**：判定は「設計判断に効くか」であって「関連しそうか」ではない。同じロール・同じファイルに触れるというだけの表面的な近さ、あるいは「ついでに知っておくとよい」程度の関連は軸2の対象にしない。軸2で集約するなら、上記2条件それぞれについてどう当てはまるかを本文に明記できることを最低条件とする。歯止めなく広げると Issue が肥大化して着手不能になる。

集約する場合は、原因が別であることを Issue 本文に明記し（同一視しない）、それぞれの観測が対策の評価軸としてどう効くかも書く。

### 2軸が食い違ったとき

軸1 は「同じ成果または root cause を扱う既存 Issue があれば止める」、軸2 は「別 root cause でも上記2条件をどちらも満たすなら材料として載せる」——どちらも集約側の判定しか定義していない。したがって食い違いは次の2通りとして現れ、いずれも解が決まっている。

- **材料は一体だが、成果は別**（軸2 が集約を指し、成果が複数に割れる）。材料は既存 Issue へ集約し、実行単位は §4 に従って分割するか `type:tracking` ＋ sub-issues へ展開する。
- **root cause は同じだが、成果は別**（軸1 が集約を指し、deploy 単位や完了判定が分かれる）。これも §4 の分割規定が効く場面であり、材料を同じ Issue に置いたまま実行単位だけを分ける。

どちらの型にも当てはめられず、集約と分割のどちらへ倒すかが決まらない境界事例だけ、**AI が独断でどちらかへ倒さない**。両軸それぞれの判定結果と、その根拠、理由付き推奨を添えて、ユーザーに判断を仰ぐ（PR7 の様式＝原案・比較・理由付き推奨を必ず添えて停止する）。ユーザーが選んだ結論に従って続行する。推奨を組み立てる比較軸として、失敗コストの非対称を使う——集約しすぎは Issue が肥大化して着手不能になるが**着手前に気づき**分割で回復できる。分割しすぎは全体像を持たない部分最適な対策となり**merge 後に判明して**回復が難しい。したがって材料は集約側へ、実行単位は分割側へ倒す。

両軸が同じ結論を指す場合、軸の衝突を理由に停止する必要はない。ただしそれは手続の免除ではない——軸1 の手続（既存 Issue への追記・reopen・sub-issue 化を根拠付きで提案し、ユーザーの選択を得る）と §1 の write 境界（Issue 作成の明示依頼は既存 Issue の破壊的変更への包括許可ではない）はそのまま適用される。ユーザー確認なしに既存 Issue を書き換えない。

## 4. Issue を単一成果に整形する

1 Issue は、完了を客観的に検証できる1成果にする。**分割の判定対象は成果であって、検討材料ではない。** 独立して完了判定できる複数の成果、別 deploy 単位、別レビュー単位が混在するなら draft を分割する。root cause が別であること自体は分割の理由にならない——別 root cause の観測を検討材料として同じ Issue へ載せる判断は §3 軸2 が扱い、ここで見るのはその材料から**複数の成果が確定したか**だけである。成果がまだ確定していない検討段階（例：方式の選択肢を洗い出し、トレードオフと推奨を添えて判断を仰ぐ）は、材料を集約したまま1成果として保つ。集約した材料から複数の成果が出た段階で分割し、`type:tracking` ＋ sub-issues へ展開する。tracking Issue は複数 sub-issues の進行を束ねるために使い、自身の実装成果と混ぜない。

本文には必ず次を入れる。

1. 冒頭: 使用する実行環境が定める AI attribution 文。
2. 目的・背景
3. 現状と根拠（再現事実、該当 path、ログ、関連URL。未確認を事実として書かない）
4. Scope
5. Out of scope
6. Acceptance criteria（`- [ ]` の検証可能な checkbox）
7. Dependencies / Related issues（なければ `なし`）

型に応じて次も加える。

- bug: 再現手順、期待結果、実際結果、環境、影響、root cause 仮説
- feature/improvement: 利用者価値、提案挙動、互換性、代替案
- maintenance/upgrade: 対象version、現version、移行・rollback、互換性、security影響
- docs: 読者、対象文書、更新後に可能になる判断/操作
- spike: 解く質問、調査境界、timebox、意思決定となる成果物
- tracking: 子Issue一覧、完了条件、非実装であること

## 5. labels と Project fields を決める

live metadata に存在する namespaced label だけを使う。legacy の `bug`、`documentation`、`enhancement` は使わない。

### Label rules

- `area:*`: 1個以上。影響領域なので複数可。
  - `area:review-system`: review_system 本体
  - `area:doc-system`: doc_system 本体・仕様資産
  - `area:harness`: hooks、agents、skills、CLI 実行基盤
  - `area:mcp`: MCP server/client・integration
  - `area:repository`: repository 共通運用、CI、構成
- `type:*`: 必ずちょうど1個。
  - `type:bug`: 期待済み挙動からの逸脱
  - `type:feature`: 新しい利用者向け能力
  - `type:improvement`: 既存能力の品質・使い勝手改善
  - `type:maintenance`: 動作価値を変えない保守・整理
  - `type:upgrade`: dependency、runtime、format のversion更新
  - `type:docs`: 文書だけで完結する成果
  - `type:spike`: 結論や判断材料を成果とする期限付き調査
  - `type:tracking`: sub-issues の進行を束ねる親
- `concern:*`: 該当時のみ複数可。現在の代表は `concern:security` と `concern:testing`。type の代用にしない。

### Project field rules

- `Workstream`: 主担当を1つだけ選ぶ。複数領域への影響は `area:*` で表す。
- `Status`: 新規は `Inbox`。作成時に `Done` にしない。
- `Priority`: `P0` は即時対応が必要な重大障害、`P1` はblocker/高影響、`P2` は通常、`P3` は低緊急度。根拠付きで提案できるが、live の必須 field へ設定する最終値を作成前 preview に出す。根拠なしに上げない。
- `Horizon`: `Now` は着手対象、`Next` は次候補、`Later` は時期未確定、`Deferred` は明示的な先送り。AI の既定値を持たない。ユーザー文面で値が明示されているか、作成前 preview で推奨値と根拠を示して対話的な確認を得た場合だけ設定する。未指定・未確認なら Issue/Project への write 前に停止する。
- `Deferred`: owner が理由と先送りを明示承認した場合だけ設定し、`Review date` も作成前に確認して必ず設定する。どちらかが未確認なら write 前に停止する。

作成前 preview には、選択 Project、labels、Workstream、Priority、Horizon、Review date、Harness、relations の最終予定値と判断根拠を出す。特に Horizon は preview の提示だけを承認とみなさず、対話的な確認でユーザーの承認を得る。

`area:harness` を付けた場合は、multi-select の `Harness` を1個以上設定する。

- `Claude Code`: Claude Code 固有の hooks、agents、settings、workflow
- `Codex`: Codex 固有の hooks、agents、skills、config
- `GitHub Copilot`: Copilot 固有の skills、prompts、agents、instructions
- `agy`: agy CLI/MCP 固有の連携・認証・委譲
- `Shared`: 複数 harness が共有する契約・同期基盤。単なる「全 harness」の省略には使わない
- `Other`: live options に専用項目がない具体的 harness に限る。本文へ harness 名と `Other` を使う理由を書く

共通契約と個別実装の両方に影響する場合は `Shared` と該当 harness を複数選択する。`area:harness` 以外では、Harness は影響が明白な場合だけ設定する。

### Project へ書き込めない実行環境での代替

Project を読み書きする手段が無い場合は **§7 の fail-close で停止する**。停止を報告した上で、
ユーザーが Issue の作成／更新を改めて明示指示した場合だけ Issue 本体を作成し、Project item と
field は変更せず、未設定項目を本文末尾へ記載する。live metadata 未取得、Horizon／Deferred の
オーナー確認、部分成功の報告を含む記載形式は [gh-create-issue の troubleshooting](../../troubleshooting/gh-create-issue.md) に従う。

## 6. relation を設計する

- parent/sub-issue: 成果の包含関係に使う。親の完了が子の完了を表すように構成する。
- blocked-by/blocking: 実行順の依存に使う。「A が終わるまで B を完了できない」なら B を A に blocked-by とする。
- related: 包含でも順序制約でもない参照に使う。

parent と blocker を同義に扱わない。既存 relation を読み、self relation、重複辺、循環を作らない。循環の可能性や向きの曖昧さがあれば relation を設定せず停止する。

## 7. 作成して read-back する

明示許可がある場合だけ、次の順序で行う。

1. title/body/labels を指定して Issue を1件作成する。
2. 短時間 poll/read-back し、選択した Project の confirmed Project item として auto-add されたか確認する。
3. 未追加なら選択した同じ Project へ明示追加する。別 Project を推測しない。追加に失敗したら fail-close で停止し、Issue URL、Project 未追加、fields 未設定という部分成功状態と回復案を報告する。Project を扱う手段自体が無い場合は §5 と [troubleshooting](../../troubleshooting/gh-create-issue.md) に従う。
4. Project item を確認できた後、live に解決した field/option ID で `Status=Inbox`、Workstream、確認済みの Priority/Horizon、必要な Review date/Harness を設定する。
5. parent/sub-issue と blocked-by/blocking を設定する。
6. Issue と Project item を再取得し、本文、labels、全 fields、relations が意図どおりか照合する。

作成時に close、`Status=Done`、archive を行わない。一部だけ成功した場合は黙って成功扱いせず、URL、成功項目、失敗項目、回復案を報告する。安全に修正できる範囲は修正後に再読込する。

利用可能な GitHub tool が body を安全に渡せるならその入力を使う。shell 経由では本文をコマンド引数へ埋め込まず、展開されない方法で用意した一時ファイルと `gh issue create --body-file <path>` を使う。`--body`、backtick、`$()`、秘密値を含む shell interpolation を避ける。

## 8. 完了報告を返す

最後に次を日本語で報告する。

- Issue のURLと番号
- title
- labels
- Project 名、Status、Workstream、Priority、Horizon、Review date、Harness
- parent/sub-issues、blocked-by/blocking、related
- 重複調査の主要結果
- 未設定、例外、追加判断が必要な項目

draft-only の場合は「未作成」と明記し、同じ項目の予定値と完成本文を提示する。
