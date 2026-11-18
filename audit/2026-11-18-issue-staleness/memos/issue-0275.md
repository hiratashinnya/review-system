# Issue #275「context-mode プラグイン導入と、注入ブロックに合わせたエージェント設計の見直し」

- URL: https://github.com/hiratashinnya/review-system/issues/275
- 状態: closed（2026-11-18取得）
- 本文: 2601文字/ 64行。全文: `../raw/issues-2026-07b.jsonl`
- AC: 2件（未チェック: 2）
- Issue参照: #274
- PR参照: なし
- 主見出し: ## 背景 | ## 干渉検証の結果 | ## 対応方針（オーナー判断） | ## 変更内容 | ## 環境側の設定（リポジトリ外・記録用） | ## 残作業
- 暫定評価: Closed・歴史的記録

## 本文内の現状・前提・依存記述（要時点照合）
- - **write 権限なし（7）** — ファイルに書けず注入の前提が成立しないため、`<artifact_policy>` を無効化して
- - `.claude/hooks/inject-governance.sh` / `governance-directives.md`（新規）— 規範の毎ターン注入（fail-open 設計）

## 点検記録
本文全体の状態・AC・リンクを走査。歴史的叙述のみでは古いと断定しない。関連先の最新状態と実コードは横断照合で検証し、未実測ACは合格扱いしない。
