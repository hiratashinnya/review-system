# Issue #835「[Tracking / Architecture Discovery] 既存開発基盤のADR・PFD・DFDを発掘し、改修時のドリフトを防ぐ」

- URL: https://github.com/hiratashinnya/review-system/issues/835
- 状態: open（2026-11-18取得）
- 本文: 5346文字/ 57行。全文: `../raw/issues-2026-11.jsonl`
- AC: 6件（未チェック: 6）
- Issue参照: #745, #787, #757, #788, #758, #789, #759, #791, #760, #794, #761, #836, #837, #838, #839, #840, #841, #842
- PR参照: #787, #788, #789, #791, #794
- 主見出し: ## 目的 | ## 対象・非対象 | ## 成果物・原則 | ## 進行順 | ## Issue #745との双方向ドリフト防止（共通契約） | ## Acceptance Criteria | ## Blocked by / Related | ## 子Issueの実番号と作業順（2026-11-15起票済み） | ### 双方向追従の窓口
- 暫定評価: 時点記述あり・現行照合候補

## 本文内の現状・前提・依存記述（要時点照合）
- ## Blocked by / Related
- - Parentは進捗管理でありハードBlocked byは不要。後続子Issueに各依存を記録。
- | 区分 | 子Issue | Blocked by | 対象 / 説明 |
- 上記7件を本Trackingの子として扱う。**GitHub native Sub-issue / blocked-byは本操作環境に登録APIがないため未設定**であり、本文の依存関係を暫定正本とする。native設定可能な別環境では本文と同じ方向・件数で登録し、反映済みか再取得で確認する。

## 点検記録
本文全体の状態・AC・リンクを走査。歴史的叙述のみでは古いと断定しない。関連先の最新状態と実コードは横断照合で検証し、未実測ACは合格扱いしない。
