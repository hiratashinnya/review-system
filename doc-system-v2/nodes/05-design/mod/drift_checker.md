**パス**: `spec_inspector/drift_checker.py`
**責務**: P-2-1（ref_version ドリフト検出・義務辺残存検出）を実現する。
**公開 I/F**: `check_drift(nodes, config) -> list[ViolationRecord]`
**依存**: domain（NodeRecord / ViolationRecord / ConfigSlice）
**依存方向**: core ← domain

> **改訂理由（MINOR バンプ v0.1→v0.2）**: DD-13 改訂に伴い、孫プロセス（P-2-1-1/P-2-1-2）を持つ P-2-1 を単独モジュールへ分割。checker.py → drift_checker.py に改名し、参照先を P-2 → P-2-1 に変更。旧 P-2-2/P-2-3/P-2-4 担当分は MOD-14/15/16 へ分離。
