# Issue #195「Codexレート制限検知をtmux画面スクレイピングから構造化API(account/rateLimits/read)へ置き換える」

- URL: https://github.com/hiratashinnya/review-system/issues/195
- 状態: closed（2026-11-18取得）
- 本文: 1984文字/ 32行。全文: `../raw/issues-2026-07a.jsonl`
- AC: 0件（未チェック: 0）
- Issue参照: #182, #194, #188, #192
- PR参照: #194
- 主見出し: ## 経緯 | ## 発見内容 | ## 受け入れ基準 | ## 深刻度・優先度 | ## 関連
- 暫定評価: Closed・歴史的記録

## 本文内の現状・前提・依存記述（要時点照合）
- Issue #182（PR #194・マージ済み）で、tmuxペイン出力のテキストを正規表現でスクレイピングしてレート制限を検知する仕組み（`RATE_LIMIT_PHRASE_RE`/`RATE_LIMIT_RESET_RE`のAND条件化）を強化した。その過程でオーナーから「そもそも画面テキスト解析ではなく`/usage`やAPIなど構造化された手段を使うべきでは」という指摘があり、調査した結果、`openai/codex`リポジトリに以下が確認された
- これは現在の`.codex/hooks/codex-rate-limit-stop-hook.sh`・`codex-rate-limit-watcher.sh`が行っているtmuxペインテキストの正規表現マッチング（誤検知/見逃しのリスクが残る、Issue #182で判明した通り）を代替しうる、遥かに信頼できる情報源。
- Medium。実害は現状のIssue #182是正で低減済みだが、根本的な設計改善であり、tmux依存の脆さ（Issue #188/#192で判明した各種の不確実性とも通底する）を解消しうる。

## 点検記録
本文全体の状態・AC・リンクを走査。歴史的叙述のみでは古いと断定しない。関連先の最新状態と実コードは横断照合で検証し、未実測ACは合格扱いしない。
