**パス**: `spec_inspector/condition_checker.py`
**責務**: P-2-3（カバレッジ属性検査・condition 語彙/FR normal/FR failure-error/TD-SPEC 整合検出）を実現する。
**公開 I/F**: `check_conditions(nodes, config) -> list[ViolationRecord]`
**依存**: domain（NodeRecord / ViolationRecord / ConfigSlice）
**依存方向**: core ← domain

> **改訂理由（新設・DD-13 改訂）**: 孫プロセス（P-2-3-1〜P-2-3-4）を持つ P-2-3 を単独モジュールへ分割。旧 checker.py（MOD-5）担当分のカバレッジ属性検査を独立化。
