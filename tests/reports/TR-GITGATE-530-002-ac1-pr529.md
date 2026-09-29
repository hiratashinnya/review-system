---
id: TD-GITGATE-530-002
version: 1
condition: boundary
result: PASS
log_ref: tests/logs/gitgate-530-002-ac1-pr529.txt
---
# 大規模 PR の差分全文取得（Issue #530 受入基準1の実測）の結果

設計は `tests/designs/TD-GITGATE-530-002.md`。生ログは `tests/logs/gitgate-530-002-ac1-pr529.txt`。

## 実測

- 測定日時：2026-09-29（UTC）／リポジトリ HEAD：`a3adb44`（PR #557 反映後の `origin/main`）
- 対象：PR #529（マージ済み・47 ファイル・現在の差分 4,750 行・249,487 バイト）

| 項目 | 結果 |
|---|---|
| T1 正解（GitHub API 生 diff） | 4,750 行・249,487 バイト・`diff --git` 47 件・SHA-256 `925ebe4e…fab027` |
| T2 `rtk gh pr diff 529 --no-compact` | T1 と SHA-256 **完全一致** |
| T3 対照 `rtk gh pr diff 529`（既定の圧縮） | 521 行・37,756 バイト（生 diff は 4,750 行・249,487 バイト）。出力バイト数が生 diff より約 85% 少なく（37,756 / 249,487 バイト）、「more changes truncated」表示あり。ただし両者は形式が異なり、差分内容の欠落割合は測っていない |
| T4 `python3 -m gitgate show-pr-diff 529` | マニフェストの bytes／lines／sha256 が保存ファイルの実測と一致。保存ファイルは T1 と SHA-256 **完全一致** |
| T5 ゲート判定（pr-reviewer） | `rtk gh pr diff 529 --no-compact` と `gitgate show-pr-diff 529` は許可。`gh pr diff … --no-compact`（rtk 無し）・`rtk gh pr diff 529`（`--no-compact` 無し）・`command gh pr diff …` は拒否 |
| T6 実ロール通し（pr-reviewer・Claude Code） | ゲート許可・1コマンドで取得したとロールが報告。ツールは「Output too large (243.6KB)」と保存先パスを表示。ロール報告は Read 8 回・見出し数 47・最初／最後の見出し・総行数 4751。見出し数と最初／最後の見出しは T1 と一致し、4751 行はロールが末尾の空行表示を含むと説明した値。各 Read の範囲と報告された末尾行の内容は記録されていないため、連続読了は自己申告である。**ハーネス保存ファイルは T1 とバイト完全一致し、保存内容の完全性を示す**。PR #529 のコメント・レビュー件数は計測前後で不変（comments=3・reviews=0） |

## 結論

T1/T2 と T4 では生 diff と取得・保存ファイルのバイト完全一致を確認した。T6 では Claude Code 経路のゲート、出力保存、ロールの自己申告を記録し、ハーネス保存ファイルが生 diff と完全一致することを確認した。一方、Read の各範囲が記録されていないため、ロールが実際に連続して末尾まで読んだことは自己申告を超えて確認できない。Codex 経路は `gitgate show-pr-diff` の保存ファイルを検証した実測であり、Codex の `pr-reviewer` ロールを通した読了実測ではない。

## 限界

- T6 のロール報告はモデル出力。見出し数・最初／最後の見出しは照合したが、Read の各範囲とロールが報告した末尾行の内容は記録されていないため、連続読了は自己申告である。
- 保存ファイルの SHA-256 完全一致はファイル内容が T1 と一致する証拠であり、ロールの Read 範囲や読了を裏付けない。ロールが数えた `diff --git` 47 件は目視集計。実ロール起動時のエージェント定義はセッション開始時のスナップショットの可能性がある（ゲート判定は起動時点のディスク上の #557 反映後スクリプトが行った）。
- Codex CLI 側のロール（spawn_agent）での通しの実測はしていない（T4 は gitgate を主文脈から直接実行した実測）。
