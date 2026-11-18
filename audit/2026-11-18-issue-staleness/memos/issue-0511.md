# Issue #511「pr-reviewer 契約が harm_detail に処置方針を書けと指示し、karte がそれを検証せず通す（#495 実装の取りこぼし）」

- URL: https://github.com/hiratashinnya/review-system/issues/511
- 状態: closed（2026-11-18取得）
- 本文: 3591文字/ 84行。全文: `../raw/issues-2026-09.jsonl`
- AC: 6件（未チェック: 6）
- Issue参照: #495, #503, #509, #431, #375, #468
- PR参照: #509
- 主見出し: ## 目的・背景 | ## 現状と根拠 | ### 1. 契約の自己矛盾（`.ai/agents/pr-reviewer.md`） | ### 2. 機械検査の不在（`karte/model.py`） | ### 3. 実際に発生した混入 | ## Scope | ## Out of scope | ## Acceptance criteria | ## 利用者価値 | ## 提案挙動 | ## 互換性 | ## 代替案
- 暫定評価: Closed・歴史的記録

## 本文内の現状・前提・依存記述（要時点照合）
- レビュー担当が契約どおりに書けば台帳が汚れない状態になる。現状は契約に従うと汚れるため、AI 側の注意力に依存している。
- - 切り分け: #375（open・pr-reviewer の finding をファイルハンドオフ化。Out of scope に「finding のスキーマの変更」を明記しており本 Issue と重複しない）
- - 競合注意: #468（open・issue-pipeline の Copilot / Codex 向け写しが正本から乖離）。同じミラー群を触るため、並列実行すると `asset_parity` / `guidance_sync` が fail-close する。着手を直列化すること。

## 点検記録
本文全体の状態・AC・リンクを走査。歴史的叙述のみでは古いと断定しない。関連先の最新状態と実コードは横断照合で検証し、未実測ACは合格扱いしない。
