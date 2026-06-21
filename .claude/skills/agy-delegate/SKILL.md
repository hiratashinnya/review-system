---
name: agy-delegate
description: ユーザーが明示起動する「Antigravity(agy)CLI への作業移譲」の入口。疎通チェックを必須ゲートにして agy-delegate エージェントへ委譲する。手順本体はエージェント側に単一ソース化（ここでは再記述しない）。
disable-model-invocation: true
---

# agy への作業移譲（agy-delegate）

Antigravity（agy CLI）へ使い捨ての well-scoped タスク（調査・スクラッチコード・画像生成・並列サブクエリ）を移譲するための**ユーザー起動の入口**。

手順・ツール使い分け・スコープ境界の**実体は [`agy-delegate` エージェント](../../agents/agy-delegate.md)に単一ソース化**してある（複製ドリフト防止）。本スキルはその入口として、起動時の不変ゲートだけを定める。

## 必須ゲート（破ってはならない）

1. **疎通チェックが先（fail-close）**：移譲の前に必ず `mcp__agy__antigravity_status` で agy MCP サーバーの疎通を確認する。
   - **クラウド/ヘッドレス環境では agy は使えない**（ローカル CLI・Windows Credential Manager 認証依存）。
   - `Overall: OK` でなければ**移譲せず停止**し、理由を報告する。推測で移譲を試みない。
2. **Windows パスで渡す**：`workspace` は `C:\...` 形式（WSL パス `/mnt/c/...` は `[WinError 267]` で失敗）。
3. **スコープ厳守**：doc-system ノード著作・`docs/`/本ファイルへの書き込み・製品コードの採用は**移譲しない**（それぞれ `*-author` / `reconciliation` 経由・実装は Python 標準ライブラリのみ＝Q5）。

## 使い方

1. 上記ゲートを満たすことを確認。
2. `agy-delegate` エージェントに委譲し、移譲したいタスク・対象 workspace（Windows パス）・期待する成果物を渡す。
3. エージェントが疎通チェック → ツール選択（ask/continue/swarm/image）→ 結果回収を行う。
4. 結果（使用ツール・workspace・要約）をユーザーへ提示。生成ファイルは必要なら `SendUserFile` で送る。

## done 条件

- [ ] 移譲前に `antigravity_status` で疎通を確認した（NG なら移譲せず停止・報告）。
- [ ] `workspace` を Windows パスで渡した。
- [ ] 依頼がスコープ内（doc-system 著作・本ファイル書き込み・製品コード採用を含まない）と確認した。
- [ ] 結果をユーザーへ提示した。
