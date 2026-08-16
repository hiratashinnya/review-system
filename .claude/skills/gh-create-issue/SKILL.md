---
name: gh-create-issue
description: GitHub Issue の draft または作成を依頼された時に、重複確認、本文作成、ラベル分類、Project fields・親子関係・依存関係の設定、作成後検証を安全に行う。作成の明示依頼がある場合だけ実作成し、draft 依頼では提示に限定する。
---

# GitHub Issue を作成する

すべての説明・質問・報告を日本語で行う。1 Issue を1つの検証可能な成果に保ち、実環境から取得した分類体系へ整合させる。

## 1. 実行境界を確定する

1. 「Issue を作成して」「起票して」など、GitHub への書き込み依頼が明示されているか確認する。明示されていなければ調査と draft の提示だけを行い、Issue、Project、relation を変更しない。
2. 対象 repository を remote、会話、GitHub 情報から特定する。推測だけで別 repository を選ばない。
3. repository の `CLAUDE.md` と、そこから参照される規約を読む。AI attribution、言語、権限、スコープ、先送りに関する規約を優先する。
4. 利用可能な GitHub tool で repository、Issue、label、Project を読み書きできるか確認し、不足する機能だけ `gh` で補う。権限不足、対象不明、規約矛盾なら fail-close で停止し、`AskUserQuestion` 相当で必要な判断または権限をユーザーへ具体的に求める。

Issue 作成の明示依頼は、別 repository、追加 Issue、先送り、課金、または既存 Issue の破壊的変更への包括許可ではない。

## 2. live metadata を取得する

作成前に毎回、対象 repository の全 label と、対象 repository に紐づく GitHub Project 候補を実環境から取得する。ユーザーが Project を明示していなければ、候補が1件の時だけ選択する。0件または複数件なら候補と推奨を提示して、Issue または Project への write 前に停止する。ユーザーが Project を明示した場合も、その Project が対象 repository を扱うことを確認する。draft-only では候補を提示するだけで選択・変更しない。

選択した Project の fields/options、`viewerCanUpdate` 相当の update 権限、Issue を同 Project へ手動追加する権限と手段を live で確認する。いずれかを確認できなければ write 前に停止する。Auto-add は公開APIから取得できる workflow の名前と enabled 状態だけを参考情報として確認する。repository/filter の適用条件詳細は公開APIから検証できないため、確認不能を停止条件にしない。label 名、Project number、field ID、option ID、repository ID、Issue ID を記憶や本文例からハードコードしない。

最低限、次を取得して名前とIDを対応付ける。

- labels: `area:*`、`type:*`、`concern:*`
- Project fields: `Status`、`Workstream`、`Priority`、`Horizon`、`Review date`、`Harness`
- relation 候補: parent、sub-issues、blocked-by/blocking

期待する名前が live metadata にない、表記が異なる、同義候補が複数ある場合は勝手に label/option を作らず停止する。差分と推奨案を示し、`AskUserQuestion` 相当でユーザー判断を得る。

## 3. open/closed の重複を調べる

open と closed の両方を検索する。タイトルの語句一致だけで判断せず、次を比較する。

- 対象 path、module、Project root
- 症状と root cause
- 目的と acceptance criteria
- parent、sub-issues、related Issue

同じ成果または root cause を扱う Issue があれば、新規作成を止める。既存 Issue への追記、reopen、sub-issue 化、または別 Issue が妥当かを根拠付きで提案し、ユーザーが新規作成を改めて選んだ場合だけ続行する。

## 4. Issue を単一成果に整形する

1 Issue は、完了を客観的に検証できる1成果にする。複数の独立した成果、別 root cause、別 deploy 単位が混在するなら draft を分割する。tracking Issue は複数 sub-issues の進行を束ねるために使い、自身の実装成果と混ぜない。

本文には必ず次を入れる。

1. 冒頭: `Claude Code (AI) が起票しました。`
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
- `Horizon`: `Now` は着手対象、`Next` は次候補、`Later` は時期未確定、`Deferred` は明示的な先送り。AI の既定値を持たない。ユーザー文面で値が明示されているか、作成前 preview で推奨値と根拠を示して `AskUserQuestion` 相当でユーザー確認を得た場合だけ設定する。未指定・未確認なら Issue/Project への write 前に停止する。
- `Deferred`: owner が理由と先送りを明示承認した場合だけ設定し、`Review date` も作成前に確認して必ず設定する。どちらかが未確認なら write 前に停止する。

作成前 preview には、選択 Project、labels、Workstream、Priority、Horizon、Review date、Harness、relations の最終予定値と判断根拠を出す。特に Horizon は preview の提示だけを承認とみなさず、`AskUserQuestion` 相当でユーザーの確認を得る。

`area:harness` を付けた場合は、multi-select の `Harness` を1個以上設定する。

### Project へ書き込めない実行環境での代替（本文への記載）

実行環境に Project を読み書きする手段が無い場合がある（例：Claude Code on the web には GitHub Projects 系の
MCP tool も `gh` CLI も無い）。この場合の既定はこれまでどおり **§7 の fail-close で停止する**こと。

停止を報告した上で**ユーザーが Issue の作成／更新を改めて明示指示した場合に限り**、Issue 本体を作成し、
設定すべき項目を**本文の末尾に次の見出しで記載する**。Project item への追加・field 設定は行わない（できない）。

```markdown
## Project fields（実行環境の制約により自動設定できず・要手動設定）

<どの手段が無くて設定できなかったかを1文で書く>
**live metadata（field ID / option 名）を取得できていないため下記は推奨値**であり、確認済みの option 名ではない。

| フィールド | 推奨値 | 根拠 |
|---|---|---|
| Project item | 未追加 | <理由> |
| Status | `Inbox` | 新規起票 |
| Workstream | <値 or **要判断**> | <根拠 or live option 未取得> |
| Priority | <値> | <根拠> |
| Horizon | **要オーナー確認（AI は既定値を持たない）** | 規約上、AI が未確認で設定してはならない |
| Review date | <値 or 不要> | `Deferred` のときは必須 |
| Harness | <値> | `area:harness` のとき1個以上 |
```

この代替を使うときの規律：

- **live metadata を取得できていない事実を明記する。** 記憶や本文例から option 名を断定しない（§2）。
  取得できない項目は値を埋めず `要判断` と書く。
- **`Horizon` は推奨値すら埋めない。** AI が既定値を持たない規定（§5）は本文記載でも変わらないため、
  常に「要オーナー確認」と書く。`Deferred` と `Review date` も同様にユーザー確認なしに書かない。
- **`Priority` は根拠を書ける場合だけ推奨値を入れる。** 根拠なしに上げない（§5）。
- 完了報告（§8）では、本節を書いたことと **Project item が未追加であること**を部分成功として明示する。
  本文に書けたことをもって「設定済み」と報告しない。

- `Claude Code`: Claude Code 固有の hooks、agents、settings、workflow
- `Codex`: Codex 固有の hooks、agents、skills、config
- `GitHub Copilot`: Copilot 固有の skills、prompts、agents、instructions
- `agy`: agy CLI/MCP 固有の連携・認証・委譲
- `Shared`: 複数 harness が共有する契約・同期基盤。単なる「全 harness」の省略には使わない
- `Other`: live options に専用項目がない具体的 harness に限る。本文へ harness 名と `Other` を使う理由を書く

共通契約と個別実装の両方に影響する場合は `Shared` と該当 harness を複数選択する。`area:harness` 以外では、Harness は影響が明白な場合だけ設定する。

## 6. relation を設計する

- parent/sub-issue: 成果の包含関係に使う。親の完了が子の完了を表すように構成する。
- blocked-by/blocking: 実行順の依存に使う。「A が終わるまで B を完了できない」なら B を A に blocked-by とする。
- related: 包含でも順序制約でもない参照に使う。

parent と blocker を同義に扱わない。既存 relation を読み、self relation、重複辺、循環を作らない。循環の可能性や向きの曖昧さがあれば relation を設定せず停止する。

## 7. 作成して read-back する

明示許可がある場合だけ、次の順序で行う。

1. title/body/labels を指定して Issue を1件作成する。
2. 短時間 poll/read-back し、選択した Project の confirmed Project item として auto-add されたか確認する。
3. 未追加なら選択した同じ Project へ明示追加する。別 Project を推測しない。追加に失敗したら fail-close で停止し、Issue URL、Project 未追加、fields 未設定という部分成功状態と回復案を報告する。実行環境に Project を扱う手段自体が無い場合は §5「Project へ書き込めない実行環境での代替」に従う。
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
