**パス**: `spec_inspector/reconciler.py`
**責務**: P-7-2（調停・本ファイル反映・草案スキーマ検証・転記）を実現する。
**公開 I/F**: `reconcile(draft_path, target_path) -> None`
**依存**: ports（FileSystemPort）, domain（NodeRecord）
**依存方向**: core ← domain / ports

> **改訂理由（新設・DD-13 改訂）**: 孫プロセス（P-7-2-1〜P-7-2-2）を持つ P-7-2 を単独モジュールへ分割。旧 author.py（MOD-9）担当分の調停・本ファイル反映を独立化。
