**パス**: `spec_inspector/collector.py`
**責務**: P-6（in-graph 集合決定・include/exclude 適用）を実現する。
**公開 I/F**: `collect_in_graph(root, config) -> list[Path]`
**依存**: ports（FileSystemPort）, domain（ConfigSlice）
**依存方向**: core ← domain / ports
