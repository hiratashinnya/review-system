**パス**: `spec_inspector/graph_coverage.py`
**責務**: P-3-1（グラフ網羅性点検・未駆動出力/未定義反応イベント/未消費入力検出）を実現する。
**公開 I/F**: `check_graph_coverage(nodes, config) -> list[ViolationRecord]`
**依存**: domain（NodeRecord / ViolationRecord / ConfigSlice）
**依存方向**: core ← domain

> **改訂理由（MINOR バンプ v0.1→v0.2）**: DD-13 改訂に伴い、孫プロセス（P-3-1-1〜P-3-1-3）を持つ P-3-1 を単独モジュールへ分割。coverage.py → graph_coverage.py に改名し、参照先を P-3 → P-3-1 に変更。P-3-2（仕様カバレッジ計測）担当分は MOD-17 へ分離。
