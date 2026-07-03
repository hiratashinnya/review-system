**パス**: `spec_inspector/verification_checker.py`
**責務**: P-2-4（検証層完結性検査・FND-TC-VERIFY 必須辺/TR result/TR log_ref 検出）を実現する。
**公開 I/F**: `check_verification(nodes, config) -> list[ViolationRecord]`
**依存**: domain（NodeRecord / ViolationRecord / ConfigSlice）
**依存方向**: core ← domain

> **改訂理由（新設・DD-13 改訂）**: 孫プロセス（P-2-4-1〜P-2-4-3）を持つ P-2-4 を単独モジュールへ分割。旧 checker.py（MOD-5）担当分の検証層完結性検査を独立化。
