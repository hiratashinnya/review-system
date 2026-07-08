**パス**: `spec_inspector/filter.py`
**責務**: P-2-5（発火・重症度確定プロセス）を実現する。
**公開 I/F**: `finalize_rule_firing(violations, config) -> list[ViolationRecord]`
**依存**: domain（ViolationRecord / ConfigSlice）
**依存方向**: core ← domain

> **改訂理由（MINOR バンプ v0.1→v0.2・issue #118 後続）**: suppress 機構廃止に伴い `apply_suppression()` 前提を撤去し、scheduled/activate_stage/always_error による発火確定・重症度確定へ責務を縮退した。`spec_inspector/` パッケージは未実装の設計記述であるため、ここでは設計 I/F の現行化に留める。
