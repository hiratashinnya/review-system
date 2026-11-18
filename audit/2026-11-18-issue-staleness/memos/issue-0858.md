# Issue #858「[Tracking / Simplification] Claude Code標準worktreeを活用し、worktree所有台帳とgitgateの重複制御を縮小・撤去する」

- URL: https://github.com/hiratashinnya/review-system/issues/858
- 状態: open（2026-11-18取得）
- 本文: 6602文字/ 75行。全文: `../raw/issues-2026-11.jsonl`
- AC: 7件（未チェック: 7）
- Issue参照: #559, #502, #859, #662, #745, #752, #753, #754, #755, #756, #694, #685, #855, #409, #839, #840
- PR参照: なし
- 主見出し: ## 目的・成果 | ## 事前調査（2026-11-17、コード読取・Issue調査・公式仕様照合。実機検証は未実施） | ## 実行計画（新規起票は段階式、実装IssueとPRは原則1:1） | ### 計画・条件分岐 | ## 既存Issue整合（**以下は変更提案。S完了前に勝手にクローズ/変更しない**） | ## 全段共通の不変条件 | ## 親IssueのAcceptance Criteria
- 暫定評価: 時点記述あり・現行照合候補

## 本文内の現状・前提・依存記述（要時点照合）
- | 現行台帳 | [`issue_start/worktree_ledger.py`](https://github.com/hiratashinnya/review-system/blob/main/issue_start/worktree_ledger.py) が `open/running/stopped/collected/release_pending/released/stale/abandoned` の8状態、dispatch→agent→w
- ※ Sの決定で実装粒度・再利用Issue・PR数を変更してよいが、**1 Issue＝1 PR原則**と重複実装抑止を維持。コード変更のないSpike/Tracking/実機検証IssueはPRを要求しない。マージはオーナー判断、通常のmerge commitを前提。
- | [#745「[Tracking / Refactor] maintainability_lint 既存負債75件を全解消する（33ファイル・領域別stack）」](https://github.com/hiratashinnya/review-system/issues/745) と子 [#752「[Maintainability I-01] SubagentStop判定・進行ポインタを分離」](https://github.com/hiratashi
- **依存（提案・native関係はSで確定）**: S→I-1→#662→#559→I-4→V。#855の「再開契約判断」は#662着手前に必要だが、#855全AC完了待ちが必要かをSで判断。#754/#755の統廃合時は#756のblocked-byを必ず更新し循環/空待ちをなくす。
- - [ ] 既存Issueの統廃合・スコープ/AC・関係・blocked-byの変更前後が記録され、GitHubへ実反映済み。

## 点検記録
本文全体の状態・AC・リンクを走査。歴史的叙述のみでは古いと断定しない。関連先の最新状態と実コードは横断照合で検証し、未実測ACは合格扱いしない。
