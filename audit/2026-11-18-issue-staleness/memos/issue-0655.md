# Issue #655「issue_start の工程入力検査が、通常の開発で出る git 無視対象ファイル（スケジューラ lock・孤児 .pyc・別 runtime の .pyc）を未追跡 source として拒否し、全 dispatch が止まる」

- URL: https://github.com/hiratashinnya/review-system/issues/655
- 状態: closed（2026-11-18取得）
- 本文: 11207文字/ 108行。全文: `../raw/issues-2026-10.jsonl`
- AC: 17件（未チェック: 0）
- Issue参照: #662, #663, #652, #1, #3, #4, #5, #6, #7, #8, #371, #538
- PR参照: なし
- 主見出し: ## 目的・背景 | ## 現状と根拠 | ### 観測（#652 の調査工程 issue-investigator dispatch が `ISSUE_START_PHASE_BINDING_INVALID` で5回連続拒否） | ### 該当コード（起票時に読取り確認） | ### 現行契約（意図的設計・覆さない） | ## Scope | ## 設計案の比較と推奨（原案） | ## Out of scope | ## Acceptance criteria | ## Dependencies / Related issues
- 暫定評価: Closed・歴史的記録

## 本文内の現状・前提・依存記述（要時点照合）
- | 1 harness lock | 1C 現状維持（毎回削除） | 変更なし。 | 現在の痛みが残る。**却下**。 |
- - 正式な parent／sub-issue／blocked-by 関係は設定しない（#652 は workaround の削除で着手可能であり、blocked-by にしない）。

## 点検記録
本文全体の状態・AC・リンクを走査。歴史的叙述のみでは古いと断定しない。関連先の最新状態と実コードは横断照合で検証し、未実測ACは合格扱いしない。
