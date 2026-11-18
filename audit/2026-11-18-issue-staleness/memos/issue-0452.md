# Issue #452「Codex issue-pipeline の implementer/fixer を隔離worktreeへ機械束縛する」

- URL: https://github.com/hiratashinnya/review-system/issues/452
- 状態: closed（2026-11-18取得）
- 本文: 17918文字/ 180行。全文: `../raw/issues-2026-08b.jsonl`
- AC: 22件（未チェック: 5）
- Issue参照: #538, #448, #449, #451, #506, #518, #520, #409, #445, #293, #337, #386, #475, #477
- PR参照: #448, #506, #518, #520, #475, #477
- 主見出し: ## 現在の扱い（2026-10-09・方式撤回） | ## 現在の進捗（2026-09-17） | ### 次に行うこと | ### P4診断で追加した未解消事項 | ### P4 implementer owner-approved change plan | ## 目的・背景 | ## 現状と根拠 | ## 採用する実行契約 | ## Scope | ## Out of scope | ## Acceptance criteria | ## 実施順（現スプリント）
- 暫定評価: Closed・歴史的記録

## 本文内の現状・前提・依存記述（要時点照合）
- ## 現在の扱い（2026-10-09・方式撤回）
- Codex AI agent がオーナーの明示指示に基づき追記しました。本Issueは旧supervisor方式の撤回を理由に `not_planned` でcloseします。#538完了までOPENで保持する従来方針を変更しました。
- P4 implementer/fixer・host publish実運用検証・F-452-31〜36は未達・未解消の履歴として保全し、成功やresolvedへ読み替えません。mainに残るsupervisorの撤去・置換と、PR #448 / #449 / #451の撤去・置換後の影響確認は #538 のScope・Acceptance criteriaへ引き継ぎ済みです。#538はOPENのまま追跡します。
- ## 現在の進捗（2026-09-17）
- | 項目 | 状態 | 現在の根拠・残作業 |
- | 独立レビュー・CI | 完了・CLEAN | canonical karte round 19で F-452-01〜14 は全件resolved、open 0。PR最終head `f791330` のGitHub Actionsは asset-parity / unittest の2件ともPASS。 |
- | P4 implementer / fixer | **診断完了・追加修正前** | 新しい独立複製で実Codex起動とthread生成までは成功。tool helper欠落で全tool callが失敗し、さらに下流監査で再実行・読取・handoff形式・commit identity・publish入力の5問題を確認。F-452-31〜36をopenとして修正する。 |
- | Issue #452 close | 未完了 | post-shrink P3、F-452-17、P4、3 PR影響確認、全AC監査が終わるまでOPENを維持する。 |
- - OpenAI 公式 Subagents: https://learn.chatgpt.com/docs/agent-configuration/subagents

## 点検記録
本文全体の状態・AC・リンクを走査。歴史的叙述のみでは古いと断定しない。関連先の最新状態と実コードは横断照合で検証し、未実測ACは合格扱いしない。
