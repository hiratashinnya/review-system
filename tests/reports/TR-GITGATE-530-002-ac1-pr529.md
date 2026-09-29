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
| T3 対照 `rtk gh pr diff 529`（既定の圧縮） | 521 行・37,756 バイトで「more changes truncated」表示あり＝**約 85% が欠落**（元の問題を実 PR で再現） |
| T4 `python3 -m gitgate show-pr-diff 529` | マニフェストの bytes／lines／sha256 が保存ファイルの実測と一致。保存ファイルは T1 と SHA-256 **完全一致** |
| T5 ゲート判定（pr-reviewer） | `rtk gh pr diff 529 --no-compact` と `gitgate show-pr-diff 529` は許可。`gh pr diff … --no-compact`（rtk 無し）・`rtk gh pr diff 529`（`--no-compact` 無し）・`command gh pr diff …` は拒否 |
| T6 実ロール通し（pr-reviewer・Claude Code） | ゲート許可・1コマンドで取得。ツールが「Output too large (243.6KB)」と保存先パスを示し、ロールはそのファイルを 8 回の連続 Read で読了。見出し数 47・最初／最後の見出し・末尾行が正解と一致。**ハーネスが保存したファイルは T1 とバイト完全一致**。PR #529 の comments／reviews は計測前後で不変（外部書込みなし） |

## 結論

Issue #530 の受入基準1（pr-reviewer で数千行級 PR の差分全文が 1 コマンドで取得できることの実測）は、Claude Code 経路（`rtk gh pr diff <N> --no-compact` ＋ ハーネスの自動保存）と Codex 経路（`gitgate show-pr-diff`）の両方で、欠落なく取得できることを確認した。

## 限界

- T6 のロール報告はモデル出力であり、正しさは主文脈の機械計測（見出し数・最初／最後の見出し・末尾行・保存ファイルの SHA-256）で独立に裏取りした。
- ロールが数えた `diff --git` 47 件は目視集計。実ロール起動時のエージェント定義はセッション開始時のスナップショットの可能性がある（ゲート判定は起動時点のディスク上の #557 反映後スクリプトが行った）。
- Codex CLI 側のロール（spawn_agent）での通しの実測はしていない（T4 は gitgate を主文脈から直接実行した実測）。
