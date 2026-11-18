# Issue #265「[Phase 3] SRC/TD/TC/TR の materialize と current_stage 前進（#160 → #161 → #162）」

- URL: https://github.com/hiratashinnya/review-system/issues/265
- 状態: open（2026-11-18取得）
- 本文: 3608文字/ 101行。全文: `../raw/issues-2026-07b.jsonl`
- AC: 4件（未チェック: 4）
- Issue参照: #261, #127, #256, #160, #161, #162, #118, #254
- PR参照: なし
- 主見出し: ## 目的 | ## 前提 | ## 本フェーズの規模（最大） | ## 着手順序 | ## 孫1 — #160: Sprint 1 対象の SRC 実装ノードを materialize | ### スコープは維持（オーナー指示・2026-07-26） | ### 被覆すべき 64 件 | ### 設計 → 実装の乖離：3 類型（素案・ノード単位の確定は本 Issue 内で実施） | ### 実装 → 設計の乖離（設計外実装・逆方向） | ## 孫2 — #161: Sprint 1 対象の TD/TC/TR 検証ノードを materialize | ## 孫3 — #162: current_stage を implementation → verification へ進める | ## 完了条件
- 暫定評価: 時点記述あり・現行照合候補

## 本文内の現状・前提・依存記述（要時点照合）
- | 対象 | 現状 | 備考 |
- | orc | 2 | **1 件のみ可** — `検査パイプライン実行`＝`doc-system-v2/validate.py:main`。`著作・反映パイプライン実行` は Claude サブエージェント担体で **#256 の担体軸導入が前提** | ⚠️ 1/2 |
- **現状 0 件・完全未着手。** body policy（**TD shared body / TC bodyless / TR result・log_ref**）と **TD-TC exactly-one**、TC-TR の実行結果証跡を満たす必要がある。
- - 前提 Issue の完了確認
- **受け入れ条件**: `current_stage: verification` で validate / drift / prompt-coverage が通る。Sprint 1 対象の open Q / open FND が残っていない。Sprint 2 / post-mvp 明示分が明確に defer されている。
- - [ ] Sprint 1 対象の open Q / open FND が残っていない

## 点検記録
本文全体の状態・AC・リンクを走査。歴史的叙述のみでは古いと断定しない。関連先の最新状態と実コードは横断照合で検証し、未実測ACは合格扱いしない。
