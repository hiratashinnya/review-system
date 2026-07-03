**パス**: `spec_inspector/parser.py`
**責務**: P-1-1〜P-1-5（パース・集合組立まで）を実現する。P-1-6（ビュー射影）は MOD-13 が担当。
**公開 I/F**: `parse_nodes(paths) -> list[NodeRecord]`
**依存**: ports（FileSystemPort）, domain（NodeRecord / EdgeRecord）
**依存方向**: core ← domain / ports

> **改訂理由（MINOR バンプ v0.1→v0.2）**: DD-13 改訂（孫プロセスあり OR 責務が明確に別 → L2 単位分割）に伴い、責務を P-1-1〜P-1-5（パース・集合組立まで）に限定。P-1-6（検査ビュー射影＝ビュー工場・別責務）は MOD-13 projector へ分離。
