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
| Harness | <値> | `area:harness` のとき1個以上 |
```

live metadata を取得できていない事実を明記し、記憶から option 名を埋めない。`Horizon`、`Deferred`、`Review date` はオーナー確認なしに設定しない。`Priority` は根拠がある場合だけ推奨値を記載する。完了報告では Project item 未追加を部分成功として明示する。

## Issue は作成できたが Project 反映に失敗した

Issue URL、成功した項目、Project 未追加、未設定 fields、relations の状態を記録して fail-close で停止する。別 Project を推測して追加しない。安全に修正できる範囲だけを修正し、read-back で確認する。修正手段が無ければ未設定項目とオーナーが行う操作を報告する。

## Claude Code でサブエージェントの draft が表示されない／表示を確認できない（Issue #632）

`gh-create-issue` サブエージェントの本文は `tmp/_handoff/gh-create-issue--<key>.md` に書かれ、SubagentStop フック（`.claude/hooks/subagent-draft-display.sh`）がチャットへ直送する。表示されないときは次の順で切り分ける。

1. 最終応答の `HANDOFF:` 行が指すファイルが存在するか確認する（`tmp/_handoff/` 直下・`gh-create-issue--<key>.md`）。無ければエージェントが書けていないので、同じ入力・新しい key で再 dispatch する。
2. 存在するのに表示されない場合、`claude --debug` の stderr で `draft-display-stop` の `reason` を見る。`NO_HANDOFF_LINE`＝最終応答に `HANDOFF:` 行が無い／`HANDOFF_UNREADABLE`＝パスが規定形（`tmp/_handoff/gh-create-issue--<英数字と ._->.md`・通常ファイル・symlink 不可）ではない。
3. フックが動いていない（stderr に `draft-display-stop` の evidence が無い）場合は、ワークスペース信頼の未受諾・フック無効化・python3 不在を疑う。復旧するまで handoff を直接 Read して提示する。主文脈は要約で代替してはならず、本文をそのまま提示する（オーナーが「表示されていない」と述べたときだけ。通常は再掲しない）。起票は draft をオーナーが確認してから行う。

表示が確認できない状態で `mode: create` の起票へ進まない（draft 提示とオーナー確認が起票の前提）。

