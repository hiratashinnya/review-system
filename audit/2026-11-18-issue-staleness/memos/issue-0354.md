# Issue #354「issue-fixer にも worktree 分離を強制する（＋既存 PR ブランチを worktree 側で取得する機構の比較検討）」

- URL: https://github.com/hiratashinnya/review-system/issues/354
- 状態: closed（2026-11-18取得）
- 本文: 3313文字/ 50行。全文: `../raw/issues-2026-08a.jsonl`
- AC: 6件（未チェック: 6）
- Issue参照: #350, #353, #323, #310, #308
- PR参照: #353
- 主見出し: ## 目的・背景 | ## 現状と根拠 | ## Scope | ## Out of scope | ## Acceptance criteria | ## Dependencies / Related issues
- 暫定評価: Closed・歴史的記録

## 本文内の現状・前提・依存記述（要時点照合）
-   - **D**: 現状維持（主文脈が手動で worktree 解放＋`git switch` する運用。`.claude/skills/issue-pipeline/SKILL.md` ②-c に commit `3344a23` で明文化済み）
- - **F-0（handoff/karte のパス契約を isolation 前提へ作り替える）の決定そのもの** — #323 に集約済み。本 Issue はその決定に依存する（下記 Dependencies）。
- - **Blocked by: #323**（F-0 = isolation 下でメインワークツリー絶対パスへ書けない問題の決定。未決のまま本 Issue を実装すると `karte_path` が書けなくなる）

## 点検記録
本文全体の状態・AC・リンクを走査。歴史的叙述のみでは古いと断定しない。関連先の最新状態と実コードは横断照合で検証し、未実測ACは合格扱いしない。
