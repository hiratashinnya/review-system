# Issue #423「SubagentStopが多段の入れ子dispatch中に誤って回収を試み、同一dispatch自身の後続委譲をブロックする」

- URL: https://github.com/hiratashinnya/review-system/issues/423
- 状態: closed（2026-11-18取得）
- 本文: 5252文字/ 70行。全文: `../raw/issues-2026-08b.jsonl`
- AC: 6件（未チェック: 6）
- Issue参照: #338, #354, #417, #418, #309
- PR参照: なし
- 主見出し: ## 目的・背景 | ## 現状と根拠（コード確認済み） | ### 遷移先・遷移条件（確認結果） | ### 根本原因：`_discover_handoff`の`"empty"`判定のオーバーロード | ### 実際に観測した失敗連鎖（Issue #338実装中に実測） | ### 影響範囲 | ## 並列dispatchについて（オーナー指摘・要検討事項として含める） | ## Scope | ## Out of scope | ## Acceptance criteria | ## Dependencies / Related issues | ## Project fields（提案・要オーナー確認）
- 暫定評価: Closed・歴史的記録

## 本文内の現状・前提・依存記述（要時点照合）
- ## 現状と根拠（コード確認済み）
- - **ただし`update_ledger`のロック（`issue_start/worktree_ledger.py` L281-355・`O_CREAT|O_EXCL`スピンロック、既定タイムアウト5秒）は、並列dispatchが同時に停止イベントを起こすと競合が増える**。今回は`LEDGER_LOCK_TIMEOUT`は観測しなかったが、上記の根本原因バグが1dispatchあたりのロック取得・解放回数を水増しするため、**根本原因バグと並列度の高さ
- - 主文脈による応急処置（`ledger.json`の直接編集）は`update_ledger`のロックを経由しない不安全な迂回だった。「このworktreeはまだ正当に使用中」を安全に主張する手段が現状存在しないこと自体が別の欠落。
-   1. **（推奨・コード修正）** `_discover_handoff`が`"empty"`を返す場合、`_release_stage`は即座に収集を試みず、他の積極的な完了シグナルが無い限り現状の`running`ステータスを保持する（何もしない）よう変更する。早期STOP（handoffを永久に書かない）の正当系については、別途明示的な完了シグナル（例：payloadの終了理由フィールド等、実際に利用可能かは要調査）を必要とする形に見直す。

## 点検記録
本文全体の状態・AC・リンクを走査。歴史的叙述のみでは古いと断定しない。関連先の最新状態と実コードは横断照合で検証し、未実測ACは合格扱いしない。
