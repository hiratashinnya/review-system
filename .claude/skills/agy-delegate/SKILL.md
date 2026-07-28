---
name: agy-delegate
description: ユーザーが明示起動する「Antigravity(agy)CLI への作業移譲」の入口。疎通チェックを必須ゲートにして agy-delegate エージェントへ委譲する（read-only 影響調査レポート・ノード素案・調査・スクラッチコード・画像生成）。手順本体はエージェント側に単一ソース化（ここでは再記述しない）。
disable-model-invocation: true
---

# agy への作業移譲（agy-delegate）

Antigravity（agy CLI）へ well-scoped タスク（read-only 影響調査＋レポート出力・ノード素案作成・調査・スクラッチコード・画像生成・並列サブクエリ）を移譲するための**ユーザー起動の入口**。

手順・ツール使い分け・スコープ境界・**ユースケース表と必読規律セット**の実体は [`agy-delegate` エージェント](../../agents/agy-delegate.md)に**単一ソース化**してある（複製ドリフト防止）。本スキルはその入口として、起動時の不変ゲートだけを定める。

> 想定ユースケース（UC-1 影響調査／UC-2 参照・孤児調査／UC-3 ノード素案／UC-4 リポジトリ外調査／UC-5 スクラッチコード／UC-6 画像生成／UC-7 並列）と、各 UC で agy に `ask` で読ませる**必読規律セット**（G-min / G-full ＋ 型別 A-\<type\>）は**エージェントの表が正本**。ランタイムでの判断ブレを抑えるため、その表に従って規律を渡すこと。

## 必須ゲート（破ってはならない）

1. **疎通チェックが先（fail-close）**：移譲の前に必ず `mcp__agy__antigravity_status` で agy MCP サーバーの疎通を確認する。
   - **クラウド/ヘッドレス環境では agy は使えない**（ローカル CLI・Windows Credential Manager 認証依存）。
   - **判定は allowlist（既定は停止）**：続行してよいのは「全項目正常」または「negative が `newest transcript` だけ（既知の transcript 書込バグ・実際の委譲は成功する）」のときだけ。**それ以外の negative・未知の項目・将来追加される診断はすべて停止**する（停止条件を列挙する方式は将来 fail-open するため採らない）。
   - **`Overall: OK` を可否の判定条件にしない**——status は**認証状態もワークスペース到達性も検査していない**（`Overall: OK` でも agy が対象ツリーを開かず答えることがある）。**「未ログインなら停止」は status では判定不能**なので停止条件に数えない（認証 probe の追加は Issue #271）。詳細＝`.claude/agents/agy-delegate.md`。
2. **workspace は `wslpath -w` の絶対パスを明示的に渡す**（省略しない）。並列系は要素ごとに指定する（swarm 相当＝`tasks[].workspace`、image swarm 相当＝`workspaces[]`）。**機械強制**＝`.claude/hooks/agy-workspace-guard.sh`。「WSL パスは `[WinError 267]` で失敗する」という旧記述は 2026-07-27 の調査で否定済み。
3. **repo 依存タスクは「実際に見えているか」を確認する**：最初の委譲で検証可能なアンカー（対象ファイルの実内容）を取らせ、`Read`/`Grep` で突き合わせる。不一致なら結果を破棄して停止・報告する。
4. **スコープ厳守（境界＝誰が正本に書くか）**：agy は**素案・調査レポートを返す read-only/draft アシスタント**。`docs/`/本ファイルへの書き込み・ノードの確定著作・無検証コード採用は**移譲しない**（`*-author`(tmp)→`reconciliation-validator`(検証)→`reconciliation`(書込) 経由・実装は Python 標準ライブラリのみ＝Q5）。✅ read-only 影響調査（例：ref_version バンプの伝搬先レポート）・ノード素案作成（規律を `ask` で読ませてから）は可。**agy にはファイルを書かせずテキスト/レポートで回収**し、正本反映は既存パイプラインに通す。

## 使い方

1. 上記ゲートを満たすことを確認。
2. `agy-delegate` エージェントに委譲し、移譲したいタスク・対象 workspace（`wslpath -w` の絶対パス）・期待する成果物を渡す。
3. エージェントが疎通チェック → ツール選択（ask/continue/swarm/image）→ 結果回収を行う。
4. 結果（使用ツール・workspace・要約）をユーザーへ提示。生成ファイルは必要なら `SendUserFile` で送る。

## done 条件

- [ ] 移譲前に `antigravity_status` を実行し、**許容条件（全項目正常／negative が `newest transcript` だけ）に一致する**ことを確認した（一致しない・未知の診断があるなら移譲せず停止・報告）。
- [ ] `workspace` を `wslpath -w` の絶対パスで明示的に渡した。
- [ ] repo 依存タスクなら、agy が対象ツリーを実際に見ていることをアンカー突き合わせで確認した。
- [ ] 依頼がスコープ内（doc-system 著作・本ファイル書き込み・製品コード採用を含まない）と確認した。
- [ ] 結果をユーザーへ提示した。
