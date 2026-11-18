# Issue #800「[#375 子1] pr-reviewer finding の信頼済みファイルハンドオフ取り込みを実装する（reviewer 専用 ingest-reviewer・PR #697）」

- URL: https://github.com/hiratashinnya/review-system/issues/800
- 状態: closed（2026-11-18取得）
- 本文: 6517文字/ 81行。全文: `../raw/issues-2026-11.jsonl`
- AC: 10件（未チェック: 10）
- Issue参照: #375, #523, #371, #697, #792, #696, #341, #797, #406, #407, #793, #369, #310, #409, #531, #337, #368
- PR参照: #697, #696
- 主見出し: ## 目的・背景 | ## 現状と根拠 | ## Scope | ## Out of scope | ## Acceptance criteria | ## 対象 harness | ## 型別の補足（improvement） | ## Dependencies / Related issues
- 暫定評価: Closed・歴史的記録

## 本文内の現状・前提・依存記述（要時点照合）
- - PR #697（draft・`agent/issue-375-reviewer-trusted-ingest`、base は下段 PR #696 の `agent/refactor-karte-ingest-split`）の本文によれば、方式はオーナー承認済み（2026-10-31）の「reviewer 専用 karte verb `ingest-reviewer`＋パス検証付き Write」である。
-   - 申告 `scope` の原本（`tmp/_karte/issue-<N>.declared-scope.jsonl`）を round 1 から保護し、保護モードの主文脈 `ingest-review` は新規 finding の追記専用にする（#523 の前提）。
- - 上記「現状と根拠」の方式の実装を、PR #697 の1本で完了させる。
- - reviewer 本人の PR コメント投稿経路、reviewer worktree 隔離の機械強制、`pr-reviewer` の素の Write が fail-open の PreToolUse hook だけに依存する点（#375 の子 Issue「reviewer の権限分離の機械強制」）。
- - [ ] (E2) producer へ一般 Write/Edit・任意 `ctx_execute` 書込を付与せず（`tmp/_handoff/pr-reviewer--<key>.md` へのパス検証付き Write のみ）、artifact 全文が主文脈を通過しない。なお、この Write 制限が PreToolUse hook の稼働を前提とする点（fail-open の限界）は別の子 Issue「reviewer の権限分離の機械強制」の AC
- - [ ] (S1) **正規の `activate`（review envelope 期待値あり）→ `ingest-reviewer` の経路では**、レビューア申告の `scope` 原本を主文脈の編集を経ずに保全し、初回取り込み（round 1）からレビューア原本と台帳・後続申告との差分を機械的に検出できる。期待値なしの `activate` による待機取消後、原本未作成の状態で主文脈の旧 `ingest-review` が先に `scope` を
- - 代替案：#375 本文の (a) `pr-reviewer` へ一般 Write／(b) `ctx_execute` 経由／(c) 現状維持＋出力削減（却下の経緯は `.ai/rationale/pr-reviewer.md`）。
- - 親：#375（本 Issue は #375 の sub-issue）。兄弟（0件の取り込み形式・実機実測・権限分離の機械強制）は #375 の sub-issue 一覧から辿れ、いずれも**本 Issue を blocked-by** とする（本 Issue の close ＝ PR #697 の統合を待つ）。
- - 関連：#371（共通 envelope）、#310（②-c のカルテ結線・E3 の消費側）、#409（AgentRun が expected artifact と ingest 結果を close 条件として参照）、#523（本 Issue の正規経路の原本保証と #797 の取消経路の原本・出所保証が前提。#523 の依存先は #800＋#797。#375 は tracking であり、#523 の独立ブロッカーにはしない）、#531（scope の

## 点検記録
本文全体の状態・AC・リンクを走査。歴史的叙述のみでは古いと断定しない。関連先の最新状態と実コードは横断照合で検証し、未実測ACは合格扱いしない。
