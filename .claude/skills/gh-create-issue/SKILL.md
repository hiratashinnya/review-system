---
name: gh-create-issue
description: GitHub Issue の draft または作成を依頼された時に、重複確認、本文作成、ラベル分類、Project fields・親子関係・依存関係の設定、作成後検証を安全に行う。作成の明示依頼がある場合だけ実作成し、draft 依頼では提示に限定する。
---

## 共通本文

この資産の共通本文は [gh-create-issue の共通本文](../../../.ai/skills/gh-create-issue/SKILL.md) にあります。手順の実体です。**Claude Code の主文脈は共通本文を読んで自分で実行しない**（コンテキストを圧迫するため）。実行主体は [`gh-create-issue` エージェント](../../agents/gh-create-issue.md)で、主文脈は下記の委譲と取り次ぎだけを行う。

## Claude Code 固有：サブエージェント専用

repository の `CLAUDE.md` と、そこから参照される規約を先に読む。Issue 本文の冒頭 attribution は `Claude Code (AI) が起票しました。` で、エージェント側が付ける。

### 1. dispatch する

`Agent`（`Task`）で `subagent_type: gh-create-issue` を起動する。dispatch prompt には次だけを渡す（手順の細部は書かない）。

- `request`: ユーザーの依頼原文と、会話で確定済みの目的・事実・関連 Issue。
- `mode`: ユーザーが「起票して」など GitHub への書き込みを明示していれば `create`、そうでなければ `draft`。
- `handoff_path`: `tmp/_handoff/gh-create-issue--<key>.md`。`<key>` は `date -u +%Y%m%dT%H%M%S%NZ` の値。**dispatch のたびに新しく採番し、同じパスを再利用しない**。
- `decisions`（再 dispatch のみ）: 直前の `QUESTIONS` へのオーナー回答の原文。
- `prior_handoff`（再 dispatch のみ）: 直前の `HANDOFF:` のパス。

### 2. 戻りを取り次ぐ

成果物（draft 本文・予定値 preview・完了報告）はSubagentStopフックが表示し、同じhandoffの隣に `<handoff-path>.receipt.json`（`status: displayed` または `fallback_required`）を書き残す。**Task完了後、主文脈は必ずreceiptをReadする**。`displayed` なら本文を再掲しない。receiptが無い／読めない／`fallback_required` ならhandoffをReadし、全文をそのまま提示してから次へ進む。SubagentStopの`additionalContext`は通知の補助にだけ使い、receipt確認の代わりにしない。hook出力が9000 serialized charactersを超える場合は一部表示せずfallback receiptを書く。最終応答の `STATUS` で分岐する。

- `NEEDS_OWNER_INPUT`: 最終応答の `QUESTIONS:` だけを `AskUserQuestion` に変換して尋ねる（詳細は表示済みの「オーナー確認事項」にある）。回答を `decisions` に原文のまま入れ、`prior_handoff` を付けて**新しい key で再 dispatch** する。
- `DRAFT_READY`: draft を表示済みであることだけを伝える。作成はユーザーが明示依頼したとき `mode: create` で再 dispatch する。
- `CREATED`: `ISSUE:` の URL を呼び出し元の次工程へ渡す。部分成功なら `SUMMARY` のとおり扱う。
- `STOPPED`: 実行環境の問題。共通本文 §1 の fail-close どおり write せず、`SUMMARY` をオーナーへ報告して判断を仰ぐ。
- receipt が `displayed` でもオーナーが表示を確認できないと述べた場合は、handoff を Read して本文をそのまま提示する（要約で代替しない）。

`HANDOFF:` 行が無い、または形式が契約と異なる応答は、サブエージェントの不具合として `SUMMARY` 相当をオーナーへ報告し、推測で GitHub を変更しない。

### 3. その他

- owner の確認・承認が必要な場面は上記の `QUESTIONS` → `AskUserQuestion` の往復で行う。確認できない場合は共通本文どおり write 前に fail-close する。
- Claude Code on the web で GitHub Projects 系の MCP tool と `gh` CLI を利用できない場合は、エージェントが `STOPPED` を返し、共通本文 §5 の「Project へ書き込めない実行環境での代替」はオーナーが改めて明示指示した場合だけ適用する。
