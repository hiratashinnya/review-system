**パス**: `spec_inspector/spec_coverage.py`
**責務**: P-3-2（仕様カバレッジ計測・FR×condition 充足集計・テーブル整形）を実現する。
**公開 I/F**: `measure_spec_coverage(nodes, config) -> CoverageReport`
**依存**: domain（NodeRecord / CoverageReport / ConfigSlice）
**依存方向**: core ← domain

> **改訂理由（新設・DD-13 改訂）**: 孫プロセス（P-3-2-1〜P-3-2-2）を持つ P-3-2 を単独モジュールへ分割。旧 coverage.py（MOD-7）担当分の仕様カバレッジ計測を独立化。
