# Issue #445「[トラッキング] issue-pipeline ロール分離・artifact・close gate の横断処置を実行する」

- URL: https://github.com/hiratashinnya/review-system/issues/445
- 状態: closed（2026-11-18取得）
- 本文: 6657文字/ 154行。全文: `../raw/issues-2026-08b.jsonl`
- AC: 12件（未チェック: 12）
- Issue参照: #310, #371, #375, #409, #368, #330, #405, #374, #386, #407, #452, #453, #370, #376, #448, #449, #451, #293, #337
- PR参照: #453, #448
- 主見出し: ## 目的・背景 | ## 現状と根拠 | ## 処置対象と成果 | ## 実行DAG | ### Wave 0: 前提整備を並行処置 | ### Wave 1: pipeline contractと新ロール | ### Wave 2: 独立可能な下流を並行処置 | ### Wave 3: karte verdict結線 | ### Wave 4: durable lifecycleとclose gate | ### Wave 5: 効果測定とtracking完了監査 | ## 「このIssueを処置して」と指示された場合の実行契約 | ## Native relation方針
- 暫定評価: Closed・歴史的記録

## 本文内の現状・前提・依存記述（要時点照合）
- - #310は`work_unit`のreview/remediationに限定してkarte verdictを生成し、#375のartifact取り込みを前提とする。
- - #407は新規AI資産が初版から規範・ADR・troubleshootingを分離するための前提であり、#405の既存blockerでもある。
- | #370 | 欠陥taxonomy/risk signalsの入力、および導入後再計測 | Wave 5までopen |
- ### Wave 0: 前提整備を並行処置
- 1. GitHubから対象Issueのstate、parent/sub-issue、blocked-by/blocking、Project Statusをfresh readする。本文のスナップショットだけで開始可否を決めない。
- 2. closed済みIssueは再open・再実装せず、成果が下流契約を満たすかだけ確認する。
- 3. openかつ未解決native blockerがないIssueをready setとする。
- - #371 blocked by #374 / #386 / #407
- - #375 blocked by #371

## 点検記録
本文全体の状態・AC・リンクを走査。歴史的叙述のみでは古いと断定しない。関連先の最新状態と実コードは横断照合で検証し、未実測ACは合格扱いしない。
