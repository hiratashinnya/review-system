# Issue #502「異常終了したサブエージェントの worktree が running のまま残り、後続 dispatch の adopt-branch が必ず詰まる（同一クラス3回目）」

- URL: https://github.com/hiratashinnya/review-system/issues/502
- 状態: closed（2026-11-18取得）
- 本文: 7295文字/ 121行。全文: `../raw/issues-2026-09.jsonl`
- AC: 9件（未チェック: 9）
- Issue参照: #493, #426, #464, #423, #409, #500
- PR参照: #500
- 主見出し: ## 目的・背景 | ## 現状と根拠 | ### 同一クラスの再発は今回で4回目 | ### 観測2：`pr-reviewer` が primary checkout を切り替えたまま戻さない（別 root cause・2026-09-08 追記） | #### 観測2の実測（2026-09-08・Issue #493 の是正ラウンド2） | #### 観測2が示す設計上の論点 | ## 影響 | ## root cause 仮説 | ## Scope | ## Out of scope | ## 互換性 | ## Acceptance criteria
- 暫定評価: Closed・歴史的記録

## 本文内の現状・前提・依存記述（要時点照合）
- | 本 Issue（観測1） | OPEN | **異常終了で `SubagentStop` 自体が発火せず、台帳が `running` のまま残る** |
- | 本 Issue（観測2・下記） | OPEN | **`pr-reviewer` がメインワークツリーを PR ブランチへ切り替えたまま `main` へ戻さない** |

## 点検記録
本文全体の状態・AC・リンクを走査。歴史的叙述のみでは古いと断定しない。関連先の最新状態と実コードは横断照合で検証し、未実測ACは合格扱いしない。
