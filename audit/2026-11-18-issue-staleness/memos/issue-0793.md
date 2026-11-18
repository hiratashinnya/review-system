# Issue #793「[書式の食い違い] binding の run_id / target_key は任意の1行を許す一方 karte review envelope は header-safe のみ受理し、該当 binding で Codex pr-reviewer が必ず失敗する（#375 / PR #697 レビュー由来）」

- URL: https://github.com/hiratashinnya/review-system/issues/793
- 状態: open（2026-11-18取得）
- 本文: 6286文字/ 94行。全文: `../raw/issues-2026-11.jsonl`
- AC: 7件（未チェック: 7）
- Issue参照: #697, #375, #792, #696
- PR参照: #697
- 主見出し: ## 目的・背景 | ## 現状と根拠 | ### karte 側（受理集合が狭い） | ### 上流 binding 側（受理集合が広い） | ### 帰結 | ## 再現手順（bug） | ## Scope | ## Out of scope | ## Acceptance criteria | ## 対象 harness | ## Dependencies / Related issues
- 暫定評価: 時点記述あり・現行照合候補

## 本文内の現状・前提・依存記述（要時点照合）
- - 前提: 対象コード（`karte/review_envelope.py`・`codex_worktree_exec/review_binding.py` ほか）は PR #697 とその下段 #696 の stack にあり、main へ統合されるまで着手できない。PR は GitHub の blocked-by の対象外のため、native relation は設定せず、前提を本文で示す。

## 点検記録
本文全体の状態・AC・リンクを走査。歴史的叙述のみでは古いと断定しない。関連先の最新状態と実コードは横断照合で検証し、未実測ACは合格扱いしない。
