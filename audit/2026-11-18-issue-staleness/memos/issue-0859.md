# Issue #859「[Spike / Architecture] Claude Code worktree標準機能の実測・既存安全契約との照合・関連Issue再編を確定する」

- URL: https://github.com/hiratashinnya/review-system/issues/859
- 状態: open（2026-11-18取得）
- 本文: 10348文字/ 131行。全文: `../raw/issues-2026-11.jsonl`
- AC: 11件（未チェック: 11）
- Issue参照: #858, #559, #502, #745, #855, #752, #753, #754, #755, #756, #662, #694, #685, #409, #839, #840, #652, #371
- PR参照: なし
- 主見出し: ## 目的・成果（調査・検証・設計判断のみ／PRなし） | ## 事前調査の結果（2026-11-17／静的調査・既存Issue読取／実機検証未実施） | ### 確認した実装事実 | ### Claude Code公式ドキュメントで確認した仕様（実環境への適用は未実測） | ## 調査対象の責務図（提案、未採用） | ## 調査・実機検証の作業分解 | ### 検証マトリクス（必須） | ## 関連Issueの統廃合・スコープ/関係変更計画（この表は**提案**） | ## 設計の比較（決定ゲート） | ## 承認後に起票する実装・検証の計画図 | ## Acceptance Criteria（S完了条件） | ## 主な参照
- 暫定評価: 時点記述あり・現行照合候補

## 本文内の現状・前提・依存記述（要時点照合）
- Claude Code内蔵の`isolation: worktree`・lock・清掃・resumeとGit標準のworktree実状態で、`issue_start/worktree_ledger.py`および`gitgate`の独自管理をどこまで置換できるか、**実測と安全契約の突合**で判断する。加えて、既存Issueを統廃合・スコープ改訂・設計改訂・native blocked-by再設定するための**実行可能な変更計画**を完成し、オーナー決定を取
- 1. [`issue_start/worktree_ledger.py`](https://github.com/hiratashinnya/review-system/blob/main/issue_start/worktree_ledger.py) に`tmp/_worktree/ledger.json`、8状態`open/running/stopped/collected/release_pending/released/stale/abandone
-  subgraph Runtime["Claude Code + Git（現在の実状態）"]
- | F. Issue再編 | 既存open Issue/PRと変更ファイル衝突、AC重複、統廃合/スコープ変更/設計変更、親子・blocked-by関係、1Issue:1PR、#745負債計測 | Issue変更前後表、依存DAG、差分本文案、起票計画 |
- | [#756「[Maintainability I-05] durable_lockとSessionStartの小規模負債を解消」](https://github.com/hiratashinnya/review-system/issues/756) | 独立機能を残す。#755を統廃合した場合のblocked-byを再設定 |
- | [#855「SendMessage による agent 再開が issue-start 系の gate／継続検査の対象外である件の、実害調査と対策」](https://github.com/hiratashinnya/review-system/issues/855) | 独立Spikeで継続し、再開境界の結論を#662前提へ反映。全部を一律にblockしない |
- **採用未決項目**: ①正式な完了と一時停止の境界、②検証済み完了証跡の一意性と永続保存先、③物理削除未了でも進行可能とする条件、④新規Issueと既存IssueへのAC割当、⑤native sub-issue/blocked-byの新DAG。選択肢・推奨・反証結果を示してオーナー判断を受ける。
- - [ ] 全関連open Issue/PRと実行済みPR、対象変更ファイルの重複を再取得し、既存Issueの**現行AC→維持/移管/変更/廃止**対応表を完成。
- - [ ] native sub-issue/blocked-by変更の前後DAG、不要ブロッカー除去、#754/#755廃止時の#756救済、PR競合回避順を定義。

## 点検記録
本文全体の状態・AC・リンクを走査。歴史的叙述のみでは古いと断定しない。関連先の最新状態と実コードは横断照合で検証し、未実測ACは合格扱いしない。
