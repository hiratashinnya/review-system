# Issue #781「feat(triage): 版付き自動仕分けポリシーとオーナー権限委譲契約を定義する」

- URL: https://github.com/hiratashinnya/review-system/issues/781
- 状態: closed（2026-11-18取得）
- 本文: 2916文字/ 40行。全文: `../raw/issues-2026-11.jsonl`
- AC: 8件（未チェック: 0）
- Issue参照: #691, #723, #683, #786, #785, #531, #523, #690, #798, #745
- PR参照: なし
- 主見出し: ## Parent / 目的 | ## 対象候補 | ## AC（PR固有） | ## Blocked by | ## Related / 境界 | ## 完了判定の証跡・責務分界（2026-11-10）
- 暫定評価: Closed・歴史的記録

## 本文内の現状・前提・依存記述（要時点照合）
- ## Blocked by
- - [最新HEADの独立Copilotレビュー](https://github.com/hiratashinnya/review-system/pull/798#pullrequestreview-5834339588)：**Approval recommended / No open issues**（2026-11-10 08:29 JST）。旧finding F-781-01〜06の修正を含むHEADに対する評価。
- - **未実施（本IssueのAC外）**：オーナーによる実際の委譲・有効化承認、feedback_ledger正規エントリの作成、信頼済みCLI検証器の運用接続（#785）、deferred実運用（#786）。`status:draft`／`auto_apply_enabled:false`／全feature flag:falseを維持する。

## 点検記録
本文全体の状態・AC・リンクを走査。歴史的叙述のみでは古いと断定しない。関連先の最新状態と実コードは横断照合で検証し、未実測ACは合格扱いしない。
