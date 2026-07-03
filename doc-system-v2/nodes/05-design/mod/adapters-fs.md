**パス**: `spec_inspector/adapters/fs.py`
**責務**: RealFsAdapter（本番）・FakeFsAdapter（テスト用シーム）として FileSystemPort を実装する。
**公開 I/F**: `RealFsAdapter`, `FakeFsAdapter`
**依存**: ports（FileSystemPort Protocol を実装）
**依存方向**: adapters ← ports
