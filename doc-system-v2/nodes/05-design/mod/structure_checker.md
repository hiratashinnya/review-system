**パス**: `spec_inspector/structure_checker.py`
**責務**: P-2-2（構造完結性検査・孤立/dangling/必須辺/階層親不在検出）を実現する。
**公開 I/F**: `check_structure(nodes, config) -> list[ViolationRecord]`
**依存**: domain（NodeRecord / ViolationRecord / ConfigSlice）
**依存方向**: core ← domain

> **改訂理由（新設・DD-13 改訂）**: 孫プロセス（P-2-2-1〜P-2-2-4）を持つ P-2-2 を単独モジュールへ分割。旧 checker.py（MOD-5）担当分の構造完結性検査を独立化。
