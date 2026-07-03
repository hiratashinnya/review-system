**パス**: `spec_inspector/author.py`
**責務**: P-7-1（著作・tmp 出力）を実現する。
**公開 I/F**: `author_nodes(...) -> D8Draft`
**依存**: ports（FileSystemPort）, domain（NodeRecord）
**依存方向**: core ← domain / ports

> **改訂理由（MINOR バンプ v0.1→v0.2）**: DD-13 改訂に伴い、孫プロセス（P-7-1-1〜P-7-1-3）を持つ P-7-1 を単独モジュールに限定。参照先を P-7 → P-7-1（著作側のみ）に変更。P-7-2（調停・本ファイル反映）担当分は MOD-18 reconciler へ分離。
