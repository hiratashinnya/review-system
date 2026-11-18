# Issue #676「agy_delegate の artifacts.py と launch_origin テストの Pyright 診断を解消する（#606 の F-606-29・F-606-30 申し送り）」

- URL: https://github.com/hiratashinnya/review-system/issues/676
- 状態: closed（2026-11-18取得）
- 本文: 2960文字/ 57行。全文: `../raw/issues-2026-10.jsonl`
- AC: 6件（未チェック: 6）
- Issue参照: #627, #606, #628, #510, #575, #637, #203
- PR参照: #627
- 主見出し: ## 目的・背景 | ## 現状と根拠 | ### F-606-29（scope in・harm none・レビュー時点の判定） | ### F-606-30（scope in・harm none・レビュー時点の判定） | ### 対象コードの所在 | ## Scope | ## Out of scope | ## Acceptance criteria | ## Dependencies / Related issues
- 暫定評価: Closed・歴史的記録

## 本文内の現状・前提・依存記述（要時点照合）
- PR #627（Issue #606 の agy-delegate 直接実行ラッパー実装・draft）のカルテ所見 F-606-29・F-606-30 の申し送り先。処置方針は、オーナー判断で「別 Issue へ申し送り」と決定済み（起票依頼で伝えられたオーナー判断）。期待する成果は Pyright 診断の解消（型契約の明確化、テストの引数型の整合）。
- - PR #627 は open の draft で、Issue #606 の AC（実機 UC・設定層の特定・WSL cwd 変換）は未達（#628 へ申し送り済み）。
- - [ ] 上記の検証は import が解決される文脈で行う。隔離 worktree の絶対パスなど import が解決されない文脈の 0 件を根拠にしない（#510 の reopen 記録）。
- - Blocked by: #606（対象コードは PR #627 にのみ存在し、#606 の成果が default branch へ到達するまで main 上で着手・完了できない。#606 の AC に「成果が default branch へ到達している」がある）

## 点検記録
本文全体の状態・AC・リンクを走査。歴史的叙述のみでは古いと断定しない。関連先の最新状態と実コードは横断照合で検証し、未実測ACは合格扱いしない。
