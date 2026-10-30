# gh-create-issue — 回復手順

## Project を扱う手段がない

Project の読み書き手段が無い場合は、Issue／Project への write 前に fail-close で停止する。ユーザーが Issue の作成または更新を改めて明示した場合だけ、Issue 本体を作成し、Project item と fields は変更せず、次の手動設定表を本文末尾へ追記する。

```markdown
## Project fields（実行環境の制約により自動設定できず・要手動設定）

<利用できない手段>
**live metadata（field ID / option 名）を取得できていないため下記は推奨値**

| フィールド | 推奨値 | 根拠 |
|---|---|---|
| Project item | 未追加 | <理由> |
| Status | `Inbox` | 新規起票 |
| Workstream | <値 or **要判断**> | <根拠 or live option 未取得> |
| Priority | <値> | <根拠> |
| Horizon | **要オーナー確認（AI は既定値を持たない）** | 未確認値を設定しない |
| Review date | <値 or 不要> | `Deferred` のときは必須 |
| Harness | <Issue 本文に明記された値 or 未指定・変更対象外> | 本文に対象 harness の記載がなければ設定しない・確認しない |
```

live metadata を取得できていない事実を明記し、記憶から option 名を埋めない。`Horizon`、`Deferred`、`Review date` はオーナー確認なしに設定しない。`Priority` は根拠がある場合だけ推奨値を記載する。Harness は本文に対象 harness が明記されている場合だけ推奨値を記載し、未記載なら「未指定・変更対象外」として質問しない。完了報告では Project item 未追加を部分成功として明示する。

## Issue は作成できたが Project 反映に失敗した

Issue URL、成功した項目、Project 未追加、未設定 fields、relations の状態を記録して fail-close で停止する。別 Project を推測して追加しない。安全に修正できる範囲だけを修正し、read-back で確認する。修正手段が無ければ未設定項目とオーナーが行う操作を報告する。

## Claude Code でサブエージェントの draft が表示されない／表示を確認できない（Issue #632）

本文は `tmp/_handoff/gh-create-issue--<key>.md` に書かれる。SubagentStop hook は、JSON化後9,000文字以内なら `systemMessage` で全文を表示し、成功／fallbackを `<handoff-path>.receipt.json` に記録する。`additionalContext` による主文脈通知は前提にしない。

1. Task完了後、主文脈は必ずreceiptをReadする。`status: displayed` なら再掲しない。receiptが無い、読めない、または `fallback_required` なら handoff をReadして全文をそのまま提示する。
2. receiptが `displayed` でもチャット表示を確認できない場合は、同じくhandoffを全文提示する。
3. stderr の `draft-display-stop` evidence に `NO_HANDOFF_LINE` があれば最終応答にパスが無い。サブエージェントの `SUMMARY` 相当を報告し、推測でGitHubを変更しない。`HANDOFF_UNREADABLE` はファイルが安全に読めない状態、`HOOK_OUTPUT_LIMIT` はhook出力上限超過である。hook起動失敗・receipt欠落も主文脈のfallback条件として扱う。

draftをオーナーが確認するまで `mode: create` の起票へ進まない。
