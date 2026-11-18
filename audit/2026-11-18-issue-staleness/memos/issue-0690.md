# Issue #690「[トラッキング] レビュー指摘の自動仕分けとAdvisory中央台帳を導入する」

- URL: https://github.com/hiratashinnya/review-system/issues/690
- 状態: closed（2026-11-18取得）
- 本文: 7109文字/ 129行。全文: `../raw/issues-2026-10.jsonl`
- AC: 13件（未チェック: 13）
- Issue参照: #375, #523, #683, #614, #513, #310, #409, #376, #524, #370, #652, #685
- PR参照: なし
- 主見出し: ## 目的・背景 | ## 現状と根拠 | ## 対象harness | ## 提案アーキテクチャ／責務 | ## 処置規則の原案 | ## Advisoryの唯一の正本 | ## Karte・ゲートとの接続 | ## 既存Issueとの担当境界・申し送り条件 | ## Out of scope | ## Acceptance criteria（tracking親） | ## 実施単位（予定するsub-issues） | ## Dependencies / Related issues
- 暫定評価: Closed・歴史的記録

## 本文内の現状・前提・依存記述（要時点照合）
- - `status: open`（当該PRで未修正）は維持。既存の `resolved` と混同しない。`disposition: advisory` と `advisory_ref`（または互換性を考慮した等価スキーマ）は別の属性として追加する。
- - [ ] 実装の独立成果をsub-issueへ分割し、責務・blocked-by/relatedを成果間で整理。tracking親自体は実装しない。
- **親tracking自体には一律のblocked-byを設定しない**。実装sub-issueの成果と先行条件を確定してから、最小限のblocked-byを設ける。各既存Issueのscopeを書き換えず、個別の申し送りとして追記する。
- - native blocked-by/related/sub-issue relationの書込経路は、利用中の接続で確認できた場合だけ設定する。本文の番号参照だけでGitHub native relationを設定したとは主張しない。

## 点検記録
本文全体の状態・AC・リンクを走査。歴史的叙述のみでは古いと断定しない。関連先の最新状態と実コードは横断照合で検証し、未実測ACは合格扱いしない。
