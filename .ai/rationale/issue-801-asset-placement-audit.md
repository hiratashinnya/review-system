# PR #846：変更ファイル全件の「現行契約 vs rationale」配置監査

> 実施：2026-11-16 ChatGPT (AI)。対象：Issue #801「finding 0件（clean）レビューの取り込み形式を定め、レビューで元 Issue の AC 充足を判定して AC チェックを更新する」・Draft PR #846「draft: review round 0件記録の基盤を追加する (#801)」。**本監査は配置責務の確認であり、PRの機能AC・未決オーナー決定・CI全合格を代替しない。**

## 適用した線引き

- **区分1（保存）**：何故その方式を選んだか、比較・却下案、オーナー判断履歴、過去インシデント、当時の実測 → `.ai/rationale/`。発見時は原文を先に移設し、現行資産側を編集。
- **区分2（実行時契約）**：現在の操作条件、検証・停止・例外規則、権限分離、API schema、使用方法、実際の現在の制約 → Skill・Agent・Guidance・README・Python実装。
- **テストと生成物**：テストは検証契約として残す。AGENTS/Copilotは共通原稿と生成hashで一致させ、governanceの配布用写しは同期hashを追随する。
- 根拠：`.claude/rules/01-principles.md`「PR8『消さない』の適用範囲」。今回の変化自体は `git` 履歴に保持し、移設した歴史は下記のrationaleへ再配置。

## 移設・是正の記録

- `.ai/skills/gh-create-issue/SKILL.md`：集約/分割の理由・失敗コスト論証 → `.ai/rationale/gh-create-issue.md`。判定2軸と単一成果規則はSkillに残す。
- `.claude/hooks/governance-directives.md`：過去の同期判断・注入選択理由 → `.ai/rationale/governance-directives.md`。現行の配送本文・同期markerは保持。
- `karte/README.md`：過去指摘、理由、改修経緯、旧owner環境のMCP観測 → `.ai/rationale/karte-review-history.md`。現行のフォーマット・fail-close・回復手順・既知の制約は維持。
- `.claude/skills/issue-pipeline/SKILL.md`：2026-10-30の実測と未完走の履歴 → `.ai/rationale/issue-pipeline.md`。detached worktree必須とSTOP条件はSkillに残す。
- `.ai/guidance/common.md`：文書パス併記の設計理由 → `.ai/rationale/common-guidance.md`。規則は維持し、AGENTS / Copilot生成物を再生成、governance markerを更新。
- `.ai/agents/pr-reviewer.md` と `karte/README.md`：将来に誤読させる「オーナー決定⑤」の日付・判断履歴を現行契約の見出しから分離。

## 全ファイル照合記録

PRの変更差分の全対象（**46ファイル**）について区分を確認。変更Python・テストはファイル全文も走査して、日付付き実測・不採用案・判断理由の混入がないことを確認。移設時の内容は動作条件を失わないよう区分2へ残した。

| 変更ファイル | 判定区分 | 点検と処置 |
|---|---|---|
| `.ai/agents/pr-reviewer.md` | 実行契約 | 実施条件・境界・書式のみ維持。過去実測や選択の正当化をrationaleへ移設 |
| `.ai/guidance/common.md` | 共通規範 | 初出の文書パス併記規則のみ維持。理由はcommon-guidance rationaleへ移設 |
| `.ai/rationale/common-guidance.md` | 保存先 | 設計理由・履歴・比較・未決分析を隔離。実行時契約の正本にはしない |
| `.ai/rationale/gh-create-issue.md` | 保存先 | 設計理由・履歴・比較・未決分析を隔離。実行時契約の正本にはしない |
| `.ai/rationale/governance-directives.md` | 保存先 | 設計理由・履歴・比較・未決分析を隔離。実行時契約の正本にはしない |
| `.ai/rationale/issue-801-review-round-ac.md` | 保存先 | 設計理由・履歴・比較・未決分析を隔離。実行時契約の正本にはしない |
| `.ai/rationale/issue-pipeline.md` | 保存先 | 設計理由・履歴・比較・未決分析を隔離。実行時契約の正本にはしない |
| `.ai/rationale/karte-review-history.md` | 保存先 | 設計理由・履歴・比較・未決分析を隔離。実行時契約の正本にはしない |
| `.ai/skills/gh-create-issue/SKILL.md` | 実行契約 | 実施条件・境界・書式のみ維持。過去実測や選択の正当化をrationaleへ移設 |
| `.ai/skills/issue-pipeline/SKILL.md` | 実行契約 | 実施条件・境界・書式のみ維持。過去実測や選択の正当化をrationaleへ移設 |
| `.claude/agents/pr-reviewer.md` | 実行契約 | 実施条件・境界・書式のみ維持。過去実測や選択の正当化をrationaleへ移設 |
| `.claude/hooks/governance-directives.md` | 配送写し | 履歴コメントを移設。現行規範とsynced-fromだけ残す |
| `.claude/skills/issue-pipeline/SKILL.md` | 実行契約 | 実施条件・境界・書式のみ維持。過去実測や選択の正当化をrationaleへ移設 |
| `.github/copilot-instructions.md` | 生成物 | 共通guidance由来の生成ファイル。原稿とhashを同期 |
| `AGENTS.md` | 生成物 | 共通guidance由来の生成ファイル。原稿とhashを同期 |
| `codex_worktree_exec/cli.py` | 実装 | 入力・出力・検証・保存・操作境界の実装。変更箇所・docstringに判断履歴の混入なし |
| `codex_worktree_exec/review_ac_input.py` | 実装 | 入力・出力・検証・保存・操作境界の実装。変更箇所・docstringに判断履歴の混入なし |
| `karte/README.md` | リファレンス | 形式・利用時条件・故障時回復は維持。過去の実測・導入根拠はrationaleへ移設 |
| `karte/ac_check_update.py` | 実装 | 入力・出力・検証・保存・操作境界の実装。変更箇所・docstringに判断履歴の混入なし |
| `karte/ac_snapshot.py` | 実装 | 入力・出力・検証・保存・操作境界の実装。変更箇所・docstringに判断履歴の混入なし |
| `karte/ac_snapshot_binding.py` | 実装 | 入力・出力・検証・保存・操作境界の実装。変更箇所・docstringに判断履歴の混入なし |
| `karte/active_pointer.py` | 実装 | 入力・出力・検証・保存・操作境界の実装。変更箇所・docstringに判断履歴の混入なし |
| `karte/ingest_notes.py` | 実装 | 入力・出力・検証・保存・操作境界の実装。変更箇所・docstringに判断履歴の混入なし |
| `karte/ingest_receipt.py` | 実装 | 入力・出力・検証・保存・操作境界の実装。変更箇所・docstringに判断履歴の混入なし |
| `karte/ingest_review.py` | 実装 | 入力・出力・検証・保存・操作境界の実装。変更箇所・docstringに判断履歴の混入なし |
| `karte/karte_parse.py` | 実装 | 入力・出力・検証・保存・操作境界の実装。変更箇所・docstringに判断履歴の混入なし |
| `karte/karte_record.py` | 実装 | 入力・出力・検証・保存・操作境界の実装。変更箇所・docstringに判断履歴の混入なし |
| `karte/karte_render.py` | 実装 | 入力・出力・検証・保存・操作境界の実装。変更箇所・docstringに判断履歴の混入なし |
| `karte/karte_rounds.py` | 実装 | 入力・出力・検証・保存・操作境界の実装。変更箇所・docstringに判断履歴の混入なし |
| `karte/owner_cli.py` | 実装 | 入力・出力・検証・保存・操作境界の実装。変更箇所・docstringに判断履歴の混入なし |
| `karte/review_report.py` | 実装 | 入力・出力・検証・保存・操作境界の実装。変更箇所・docstringに判断履歴の混入なし |
| `karte/review_round_record.py` | 実装 | 入力・出力・検証・保存・操作境界の実装。変更箇所・docstringに判断履歴の混入なし |
| `karte/review_summary.py` | 実装 | 入力・出力・検証・保存・操作境界の実装。変更箇所・docstringに判断履歴の混入なし |
| `karte/review_summary_ac.py` | 実装 | 入力・出力・検証・保存・操作境界の実装。変更箇所・docstringに判断履歴の混入なし |
| `karte/reviewer_cli.py` | 実装 | 入力・出力・検証・保存・操作境界の実装。変更箇所・docstringに判断履歴の混入なし |
| `karte/vocabulary.py` | 実装 | 入力・出力・検証・保存・操作境界の実装。変更箇所・docstringに判断履歴の混入なし |
| `tests/unit/test_codex_ac_snapshot_input.py` | 自動テスト | 検証データ・期待値のみ。判断経緯の混入なし |
| `tests/unit/test_codex_zero_finding_e2e.py` | 自動テスト | 検証データ・期待値のみ。判断経緯の混入なし |
| `tests/unit/test_karte_ac_finding_verdict.py` | 自動テスト | 検証データ・期待値のみ。判断経緯の混入なし |
| `tests/unit/test_karte_ac_reviewer_binding.py` | 自動テスト | 検証データ・期待値のみ。判断経緯の混入なし |
| `tests/unit/test_karte_ac_snapshot_update.py` | 自動テスト | 検証データ・期待値のみ。判断経緯の混入なし |
| `tests/unit/test_karte_model_compat.py` | 自動テスト | 検証データ・期待値のみ。判断経緯の混入なし |
| `tests/unit/test_karte_owner_failure_order.py` | 自動テスト | 検証データ・期待値のみ。判断経緯の混入なし |
| `tests/unit/test_karte_review_round_receipts.py` | 自動テスト | 検証データ・期待値のみ。判断経緯の混入なし |
| `tests/unit/test_karte_review_summary.py` | 自動テスト | 検証データ・期待値のみ。判断経緯の混入なし |
| `tests/unit/test_operation_confirmation_policy.py` | 自動テスト | 検証データ・期待値のみ。判断経緯の混入なし |

## 別軸の未完了条件（混同しない）

- 最新PRの**機能・AC審査**は引き続き独立レビューのF-801-06/08/09/10を解消して確認する。配置監査の完了を機能の承認に使わない。
- **①AC未観測の分類と語彙・③既存チェックACの後退停止**はオーナーとの決定と機械ゲートが必要。rationaleで検討しただけでは決定済みにならない。
- 最新の `asset-parity check`、`guidance-sync check`、governance同期テスト、全unittest、maintainability_lint は最新SHAのCI結果で確認する。未実行・中断・失敗を合格扱いしない。
- Issue本文のACチェック状態の自動更新やPRマージは本配置監査の対象外。
