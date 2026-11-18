# Issue #108「dsv2: ダッシュボード(open Q/FND/DD等)の自動集計サブコマンド」

- URL: https://github.com/hiratashinnya/review-system/issues/108
- 状態: closed（2026-11-18取得）
- 本文: 1137文字/ 20行。全文: `../raw/issues-2026-07a.jsonl`
- AC: 0件（未チェック: 0）
- Issue参照: #76
- PR参照: なし
- 主見出し: ## 背景 | ## やりたいこと | ## 優先度 | ## 参照
- 暫定評価: Closed・歴史的記録

## 本文内の現状・前提・依存記述（要時点照合）
- issue #76（doc-system v1→v2 フォーマット根本刷新）のカットオーバーで `doc-system-v2/00-dashboard.md` を新設した。v1 の `doc-system/00-dashboard.md` は open FND/Q/DD/PEND のサマリを著者が手で維持していたが、v2 でも同様に**手動著作の暫定版**として作成した（オーナー方針：自動化は別issueへ切り出し）。
- `doc-system-v2/nodes/04-verification/{fnd,q,dd,pend}/**` を走査し、open/decided/deferred 等の未決ノードを自動集計して `00-dashboard.md`（または生成物として別ファイル）に反映するサブコマンドを `dsv2`（`dsv2/cli.py`）に追加する。
- - `python3 -m dsv2 dashboard` （または `dsv2 pending-summary` 等）で、`nodes/04-verification/fnd/open/**`・`q/open/**`・`dd/decided/**`（未クローズ相当）・`pend/deferred/**` を走査し、title・scheduled・stage/status を集計したMarkdownテーブルを出力する。

## 点検記録
本文全体の状態・AC・リンクを走査。歴史的叙述のみでは古いと断定しない。関連先の最新状態と実コードは横断照合で検証し、未実測ACは合格扱いしない。
