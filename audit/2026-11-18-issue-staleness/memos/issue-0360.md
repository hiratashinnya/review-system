# Issue #360「docs(harness): PR #358 で同時に処置すべきだった残件3件（README の ctx_* stale・SKILL ②-d の worktree 解放手順・エージェント定義のセッション固定）」

- URL: https://github.com/hiratashinnya/review-system/issues/360
- 状態: closed（2026-11-18取得）
- 本文: 4878文字/ 81行。全文: `../raw/issues-2026-08a.jsonl`
- AC: 6件（未チェック: 6）
- Issue参照: #323, #358, #303, #304, #312, #350, #353, #309, #310, #354, #355
- PR参照: #358, #353
- 主見出し: ## 目的・背景 | ## 現状と根拠（3件） | ### ① `.claude/hooks/README.md` の ctx_* 記述が stale | ### ② `issue-pipeline` SKILL ②-d に実装者 worktree の解放手順が無い | ### ③ エージェント定義の変更が同一セッション内では反映されない | ## Scope | ## Out of scope | ## Acceptance criteria | ## Dependencies / Related issues
- 暫定評価: Closed・歴史的記録

## 本文内の現状・前提・依存記述（要時点照合）
- ## 現状と根拠（3件）
- - **Closes #312**（本 Issue の ① が #312 の唯一の未達 AC。他4件は PR #358 の `tests/unit/test_governance_sync.py` で充足済み＝テスト存在・不一致で fail・fail メッセージに現在値と記録値の両方・全テスト pass）。

## 点検記録
本文全体の状態・AC・リンクを走査。歴史的叙述のみでは古いと断定しない。関連先の最新状態と実コードは横断照合で検証し、未実測ACは合格扱いしない。
