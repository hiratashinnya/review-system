# Issue #694「工程 dispatch の作業面の契約と失敗後の回復、および hook の信頼境界の残り（#685 の範囲外の観測）」

- URL: https://github.com/hiratashinnya/review-system/issues/694
- 状態: open（2026-11-18取得）
- 本文: 21055文字/ 313行。全文: `../raw/issues-2026-10.jsonl`
- AC: 32件（未チェック: 32）
- Issue参照: #685, #662, #426, #655, #559, #603, #270, #354, #597, #502, #409, #652, #663
- PR参照: なし
- 主見出し: ## 目的・背景 | ### 読み方 | ## 現状と根拠 | ### 項目一覧 | ### (1) adopt-branch のローカル ref tip 検査と gate の食い違い（F-685-34） | ### (2) 失敗した後続作者の entry が最新 owner に残る | ### (3) dispatch 後の作業面の契約が無い | ### (4) 助言・注入用 hook の heredoc python が cwd を import 経路に含む | ### (5) 作者の worktree で実行する CLI の信頼境界 | ### (6) Codex の hook の信頼起点（Codex 側・未確認） | ### (7) cd 方式の起動口のフォールバック | ### (8) クォートなしの `${CLAUDE_PROJECT_DIR}`
- 暫定評価: 時点記述あり・現行照合候補

## 本文内の現状・前提・依存記述（要時点照合）
- Issue #685（issue_start の非初回 dispatch 検査が dispatch 元 cwd の対象 branch 上 checkout を要求し、adopt-branch が未 checkout を要求する矛盾）を修正する PR（branch `claude/issue-685-phase-target-detached-ok`、**PR 作成前**）の独立レビュー（第1〜7回）で、#685 の範囲外の観測を11項目得た。#685 の 
- | 10 | phase_tool_gate の異常時が fail-open、`-P` が Python 3.11 未満で全 Write/Edit を止めうる | 信頼境界 | 未判定 | オーナー |
- - 【確認済み】`python3 - … <<'…'` 形で起動する箇所：`.claude/hooks/inject-governance.sh:43`、`orchestrator-context.sh:41`、`check-governance-drift.sh:41`、`report-ci-anomalies.sh:41`、`codex-hook-trust-check.sh:22`。いずれも冒頭または近傍のコメントで fail-open の助言・注入
- - 【確認済み】上記の python は失敗を fail-open に吸収している（`inject-governance.sh:43-70` の `if ! payload=…`、`check-governance-drift.sh:41` の `|| warn`、`report-ci-anomalies.sh:41` の `|| true`）。このため、`-P` が使えない Python 3.11 未満でそのまま `-P` を足すと、**注入が黙って無効
- - 【申告】同じ形の hook：stop-gate、receipt-gate、karte-inject、worktree-bind、draft-display、karte-notify、adr-notify、session-start-worktree-release（起票者は前2者のみ読んだ）。
- - 【申告】同列挙に無いもの：`gh-create-issue-receipt-gate.sh`、`subagent-karte-inject.sh`、`subagent-worktree-bind.sh`、`subagent-stop-gate.sh`、`subagent-draft-display.sh`、`karte-notify.sh`、`adr-notify.sh`、`report-ci-anomalies.sh`、`session-start-
- ### (10) phase_tool_gate の fail-open と `-P` の下限
- | 項 | 現状 | 確度 |
- | A | 現状維持（手順書の順序に委ねる） | 変更なし | (2) の回復策が無い間は、失敗が entry を残す残余リスクが続く |

## 点検記録
本文全体の状態・AC・リンクを走査。歴史的叙述のみでは古いと断定しない。関連先の最新状態と実コードは横断照合で検証し、未実測ACは合格扱いしない。
