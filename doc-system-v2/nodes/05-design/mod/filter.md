**パス**: `spec_inspector/filter.py`
**責務**: P-2-5（抑制・発火フィルタ）を実現する。
**公開 I/F**: `apply_suppression(violations, config) -> list[ViolationRecord]`
**依存**: domain（ViolationRecord / ConfigSlice）
**依存方向**: core ← domain
