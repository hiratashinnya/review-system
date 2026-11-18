# Issue #460「GitHub Project の Status 自動同期の機構を実装する（手動 dispatch まで・cron 有効化は #470）」

- URL: https://github.com/hiratashinnya/review-system/issues/460
- 状態: closed（2026-11-18取得）
- 本文: 13986文字/ 197行。全文: `../raw/issues-2026-08b.jsonl`
- AC: 25件（未チェック: 25）
- Issue参照: #465, #470, #345, #363, #461, #376, #466, #467, #468, #469, #368, #371
- PR参照: #465
- 主見出し: ## 目的・背景 | ## 現状と根拠 | ## Scope | ### 1. 同期ツール（新規モジュール・既定 dry-run） | ### 2. ワークフロー（新規・`blocker-snapshot.yml` からは分離） | ### 3. `/issue-pipeline` の着手手順（③） | ### 4. PAT | ### 5. テスト | ## Out of scope | ## Acceptance criteria | ## Dependencies / Related issues
- 暫定評価: Closed・歴史的記録

## 本文内の現状・前提・依存記述（要時点照合）
- GitHub Project「review-system Development」の `Status` は現在 GitHub 標準の built-in workflow だけで駆動されており、盤面が実態からずれる区間が2つ残っている。
- - 有効な built-in workflow は8件（2026-08-31 時点・GraphQL `ProjectV2.workflows` で確認）。`Item added to project` / `Auto-add to project` / `Auto-add sub-issues to project` / `Pull request linked to issue`（オーナーが `In review` へ設定済み）/ `Pull reque
- - **Actions の `GITHUB_TOKEN` では Projects V2 に書き込めない**（`permissions:` の `repository-projects` は旧 classic projects 用）。現在このリポジトリの secrets は0件。
- | `OPEN_BLOCKER` | `blocked_by` を**推移的に**辿って open が1件以上 | → `Blocked` |
- | `CLOSURE_OPEN_DESCENDANT` | **closed の親**に open の子がいる | Status を書かず**警告**（グラフ不整合） |
- **親子関係は `Blocked` の判定に使わない。** `evaluate_closure_invariant` は `if parent_state is IssueClass.OPEN: continue` で **open な親を skip** しており、gate 自身が「未完了の子を持つ open な親」をブロック扱いしていないため。親子の不変条件は「子が残っているのに親を閉じるな」という閉じ方の規則であって、着手を妨げる依存ではない。
- | 現在の Status | ブロッカーあり | ブロッカーなし |
- - **cron 有効化時の既知の注意点**：`schedule` で発火した run では `inputs.apply` が空文字になる。現在の実装は `[ "${APPLY:-false}" = "true" ]` で判定するため空文字は dry-run 側に倒れる。つまり `schedule` を足すだけでは cron 実行が永久に dry-run になるので、#470 で手当てが要る。
- > **訂正（2026-08-31・Claude Code (AI) が実施）**：本節は当初「fine-grained PAT の Account permissions → Projects: Read and write」と記載していたが、**誤りだった**。fine-grained PAT に user 所有 Projects V2 用の権限は存在しない（上記「現状と根拠」参照）。オーナーが実際にトークン発行画面で該当項目が無いことを確認し、公式ド

## 点検記録
本文全体の状態・AC・リンクを走査。歴史的叙述のみでは古いと断定しない。関連先の最新状態と実コードは横断照合で検証し、未実測ACは合格扱いしない。
