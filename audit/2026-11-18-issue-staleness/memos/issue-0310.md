# Issue #310「refactor(issue-pipeline): 是正ループ ②-c をカルテ機構へ書き換え実害基準とエスカレーション条件を明文化する」

- URL: https://github.com/hiratashinnya/review-system/issues/310
- 状態: open（2026-11-18取得）
- 本文: 9619文字/ 193行。全文: `../raw/issues-2026-08a.jsonl`
- AC: 9件（未チェック: 9）
- Issue参照: #371, #409, #375, #350, #308, #309, #369, #354, #383, #387, #423, #307, #339, #330, #405, #406, #407, #691, #783, #784, #785
- PR参照: なし
- 主見出し: ## #371 / #375 / #409 接続条件 | ### 追加Acceptance criteria | ## 目的・背景 | ## 現状（2026-08-25 時点・main `8fe3933` を直接確認） | ### 既に完了している項目（他 Issue が先取りし、本 Issue のスコープから消えたもの） | ### 未完了（本 Issue に残る本来のスコープ） | ## 提案挙動 | ## Scope | ## Out of scope | ## Acceptance criteria | ## Dependencies / Related issues | ## Project fields
- 暫定評価: 時点記述あり・現行照合候補

## 本文内の現状・前提・依存記述（要時点照合）
- - #375のreview artifact保存・厳格parse・`ingest-review`成功後にのみstatusを評価する。このため本Issueを#375にblocked-byとする。
- ## 現状（2026-08-25 時点・main `8fe3933` を直接確認）
- `CLAUDE.md`／`governance-directives.md` を手で同期する」という前提だったが、その前提自体が
-   現在は `.ai/skills/issue-pipeline/SKILL.md` を共通正本として全 PF（`.claude/` `.agents/` `.codex/`）が
- - **`blocked by #308` / `blocked by #309`**：両方とも CLOSED。ブロック解消済み。
-   この自動注入を前提に「`karte status` の verdict/escalate を根拠に続行・停止を判定する」と書き換える。
-   上記自動注入を前提とした記述へ更新。
-       （現状のプローズ「実害と無進捗を基準に」から、機械判定への参照へ）。
- - ~~blocked by #308~~ → **CLOSED**（解消済み）

## 点検記録
本文全体の状態・AC・リンクを走査。歴史的叙述のみでは古いと断定しない。関連先の最新状態と実コードは横断照合で検証し、未実測ACは合格扱いしない。
