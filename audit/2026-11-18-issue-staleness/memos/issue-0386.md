# Issue #386「[調査] issue-pipeline agentのtools宣言・実効ツール・呼出形式を検証する」

- URL: https://github.com/hiratashinnya/review-system/issues/386
- 状態: closed（2026-11-18取得）
- 本文: 3118文字/ 86行。全文: `../raw/issues-2026-08b.jsonl`
- AC: 3件（未チェック: 3）
- Issue参照: #371, #405, #372, #406, #407
- PR参照: なし
- 主見出し: ## 横展開対象 | ## 目的・背景 | ## 現状と根拠（実測・Issue #372 実装セッションで発生） | ## Scope | ## Out of scope | ## Acceptance criteria | ## Dependencies / Related issues | ## Project fields（提案・要オーナー確認） | ## 【追記】前提変化の申し送り（Claude Code (AI)・2026-09-05・Issue #405 全オープンIssue影響点検）
- 暫定評価: Closed・歴史的記録

## 本文内の現状・前提・依存記述（要時点照合）
- ## 現状と根拠（実測・Issue #372 実装セッションで発生）
- - Bash 経由のファイル検索を層2 allowlist で新たに許可すること（Grep/Glob 付与で解決する前提）。
-       （机上確認で済ませない。Issue #372 の「エージェント定義のスナップショットが作業ツリーの現在値に
- ## 【追記】前提変化の申し送り（Claude Code (AI)・2026-09-05・Issue #405 全オープンIssue影響点検）
- 対応要否・実施時期はオーナー判断（本追記は前提変化の記録のみで、対応不要とは判断していない）。

## 点検記録
本文全体の状態・AC・リンクを走査。歴史的叙述のみでは古いと断定しない。関連先の最新状態と実コードは横断照合で検証し、未実測ACは合格扱いしない。
