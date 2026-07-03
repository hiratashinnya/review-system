**パス**: `spec_inspector/config.py`
**責務**: P-5（config 読込・スキーマ検証・スライス組立）を実現する。
**公開 I/F**: `load_config(path) -> ConfigSlice`
**依存**: ports（FileSystemPort）, domain（ConfigSlice）
**依存方向**: core ← domain / ports
